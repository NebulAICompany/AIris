from backend.shared.logger import get_logger
from backend.shared.constants import openai_client, ZEMBEREK_JAR_PATH_STR
from typing import List, Dict, Tuple
import re
import base64
from typing import Optional
import os

logger = get_logger("QUERY_UTILS")

try:
    import jpype
    from jpype import JClass, getDefaultJVMPath, startJVM

    if not jpype.isJVMStarted():
        jvmPath = getDefaultJVMPath()
        logger.debug(f"JVM Path: {jvmPath}")
        startJVM(jvmPath, "-ea", f"-Djava.class.path={ZEMBEREK_JAR_PATH_STR}")

    TurkishMorphology = JClass("zemberek.morphology.TurkishMorphology")
    turkish_morphology = TurkishMorphology.createWithDefaults()

    TurkishSpellChecker = JClass("zemberek.normalization.TurkishSpellChecker")
    turkish_spell_checker = TurkishSpellChecker(turkish_morphology)

    ZEMBEREK_AVAILABLE = True

except ImportError as e:
    turkish_spell_checker = None
    ZEMBEREK_AVAILABLE = False
    logger.error(f"Zemberek library not found: {e}")



def spell_check(query: str) -> str:
    if not query or not isinstance(query, str):
        return ""

    if not ZEMBEREK_AVAILABLE:
        return query

    try:
        words = query.split()
        corrected = []

        for word in words:
            # Sadece noktalama işaretlerinden oluşan kelimeleri atla
            if all(c in ",.?!;:()[]{}'\"-" for c in word):
                corrected.append(word)
                continue

            normalized_word = normalize_repeated_chars(word)

            # Yazım hatası kontrolü ve düzeltme önerisi
            if not turkish_spell_checker.check(normalized_word):
                suggestions = turkish_spell_checker.suggestForWord(normalized_word)
                if suggestions and len(suggestions) > 0:
                    corrected.append(str(suggestions[0]))
                else:
                    corrected.append(normalized_word)
            else:
                corrected.append(normalized_word)
        return " ".join(corrected)

    except Exception as e:
        return query


def detect_language(query: str) -> str:
    try:
        from backend.shared.constants import text_analytics_client
        response = text_analytics_client.detect_language(documents=[query], country_hint='tr')[0]
        return response.primary_language.name

    except Exception as err:
        logger.error("Encountered exception. {}".format(err))


def normalize_repeated_chars(word: str) -> str:
    if not word or not isinstance(word, str):
        return word

    result = []
    i = 0

    while i < len(word):
        char = word[i]
        result.append(char)
        repeat_count = 1

        j = i + 1
        while j < len(word) and word[j] == char:
            repeat_count += 1
            j += 1

            if repeat_count == 2:
                result.append(char)

        i = j

    return "".join(result)


def reflect_and_retry(
        prompt: str, initial_answer: str, max_retries: int = 2
) -> str:
    current_answer = initial_answer
    retry_count = 0

    while retry_count < max_retries:
        reflection_prompt = f"""
        Evaluate the following question and answer pair:

        Question: {prompt}

        Answer: {current_answer}

        Please evaluate the answer based on these criteria:
        1. Completeness: Does it fully address all aspects of the question?
        2. Accuracy: Is the information correct and well-supported by sources?
        3. Clarity: Is the reasoning process clear and well-structured?
        4. Source Attribution: Are all sources properly cited?

        Provide your evaluation in this format:
        Completeness: [Score 1-5]
        Accuracy: [Score 1-5]
        Clarity: [Score 1-5]
        Source Attribution: [Score 1-5]
        Overall Assessment: [Pass/Fail]
        Improvement Suggestions: [List specific areas for improvement]
        """

        # Use the agent for reflection
        reflection_result = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "you are a helpful assistant that evaluates answers."},
                {"role": "user", "content": reflection_prompt },
            ],
            max_tokens=800,
            temperature=0.0,
        )
        reflection = reflection_result.choices[0].message.content.strip()

        # Check if the answer needs improvement
        if "Overall Assessment: Fail" in reflection:
            retry_count += 1
            if retry_count < max_retries:
                # Create an enhanced prompt with the reflection feedback
                enhanced_prompt = f"""
                Previous Answer: {current_answer}

                Evaluation Feedback: {reflection}

                Please provide an improved answer addressing the feedback above.
                """
                # Get improved answer using the agent
                result = openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant that gets improved answer."},
                        {"role": "user", "content": enhanced_prompt },
                    ],
                    max_tokens=800,
                    temperature=0.0,
                )
                current_answer = result.choices[0].message.content.strip()
        else:
            return current_answer

    return current_answer


def extract_image_references_from_context(local_context: str) -> Tuple[str, List[str]]:
    """
    Analyze local context for image references and extract image paths.
    Returns (cleaned_context, image_paths_list)
    """
    image_pattern = r'\(\(Image\):([^)]+)\)'
    image_paths = []

    logger.debug(f"🔍 Analyzing local context for image references...")

    # Find all image references in the context
    matches = re.findall(image_pattern, local_context)

    if matches:
        logger.debug(f"   - Found {len(matches)} image references in context")
        for match in matches:
            image_path = match.strip()
            if image_path not in image_paths:
                image_paths.append(image_path)

        # Clean the context from image references
    cleaned_context = re.sub(image_pattern, '', local_context)

    return cleaned_context, image_paths


def load_images_from_paths(image_paths: List[str]) -> List[Dict]:
    """
    Load actual image files based on the extracted paths and convert to base64.
    Returns list of image data dictionaries.
    """
    images_data = []

    if not image_paths:
        return images_data

    logger.debug(f"📁 Loading {len(image_paths)} images from filesystem...")

    for path in image_paths:
        # Construct the full image path - try both .jpg and .png
        for ext in ['.jpg', '.png']:
            image_file_path = f"backend/images/{path}{ext}"

            if os.path.exists(image_file_path):
                try:
                    with open(image_file_path, "rb") as img_file:
                        img_data = base64.b64encode(img_file.read()).decode('utf-8')
                        images_data.append({
                            "filename": f"{path}{ext}",
                            "data": img_data,
                            "reference": path,
                            "type": f"image/{ext[1:]}"
                        })
                    break
                except Exception as e:
                    logger.error(f"   ❌ Error loading image {path}{ext}: {e}")

    return images_data

def filter_docs_by_selected_files(
    docs: List, selected_files: Optional[List[str]]
) -> List:
    """
    Filter retrieved documents to only include those from selected files.
    If selected_files is None or empty, return all documents.
    """
    if not selected_files or len(selected_files) == 0:
        return docs

    filtered_docs = []
    for doc in docs:
        metadata = doc.get("metadata", {})
        file_name = metadata.get("file_name", "")

        # Check if this document's file is in the selected files list
        if file_name in selected_files:
            filtered_docs.append(doc)

    logger.debug(
        f"   - Filtered {len(docs)} docs to {len(filtered_docs)} based on selected files"
    )
    return filtered_docs
