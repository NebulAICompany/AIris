from backend.shared.logger import get_logger
from backend.shared.constants import openai_client, ZEMBEREK_JAR_PATH_STR
from typing import List
from typing import Optional

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




def refine_query(user_query, lang: str = "Turkish") -> str:
    from backend.core.prompts import refinement_prompt

    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": f"{refinement_prompt} Give your answer in {lang} language."},
            {"role": "user", "content": user_query}
        ],
        temperature=0.0,
    )
    return response.choices[0].message.content
