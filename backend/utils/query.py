from backend.shared.logger import get_logger
from backend.shared.constants import openai_client, OPENAI_MODEL
from typing import List
from typing import Optional
from pydantic import BaseModel

logger = get_logger("QUERY_UTILS")


class RefinedQuery(BaseModel):
    """Structured output for query refinement"""

    refined_query: str
    keywords: List[str]


def detect_language(query: str) -> str:
    try:
        from backend.shared.constants import text_analytics_client

        response = text_analytics_client.detect_language(
            documents=[query], country_hint="tr"
        )[0]
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


def refine_query(user_query, lang: str = "Turkish") -> RefinedQuery:
    """
    Refine user query and extract keywords for search optimization

    Args:
        user_query: Original user query
        lang: Language for the response

    Returns:
        RefinedQuery: Structured output with refined query and keywords
    """
    from backend.core.prompts import refinement_prompt

    try:
        response = openai_client.chat.completions.parse(
            model=OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": f"{refinement_prompt} Give your answer in {lang} language.",
                },
                {"role": "user", "content": user_query},
            ],
            response_format=RefinedQuery,
        )
        return response.choices[0].message.parsed
    except Exception as e:
        logger.error(f"Error in structured query refinement: {e}")
        return RefinedQuery(refined_query=user_query, keywords=[user_query])
