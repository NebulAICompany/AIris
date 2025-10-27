from backend.shared.logger import get_logger
from backend.shared.constants import openai_client, OPENAI_MODEL
from typing import List
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
