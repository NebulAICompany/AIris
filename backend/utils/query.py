from backend.shared.logger import get_logger
from backend.shared.constants import openai_client, OPENAI_MODEL
from typing import List
from pydantic import BaseModel

logger = get_logger("QUERY_UTILS")


class RefinedQuery(BaseModel):
    """Structured output for query refinement"""

    refined_query: str
    keywords: List[str]


def refine_query(user_query) -> RefinedQuery:
    """
    Refine user query and extract keywords for search optimization

    Args:
        user_query: Original user query

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
                    "content": f"{refinement_prompt}",
                },
                {"role": "user", "content": user_query},
            ],
            response_format=RefinedQuery,
        )
        return response.choices[0].message.parsed
    except Exception as e:
        logger.error(f"Error in structured query refinement: {e}")
        return RefinedQuery(refined_query=user_query, keywords=[user_query])
