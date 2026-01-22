import time
from typing import Tuple, List, Dict, Any
from backend.monitoring.metrics import llm_duration_seconds
from backend.shared.logger import get_logger

logger = get_logger("AGENT_RUNNER")


async def generate_answer(
    prompt: str, agent: Any
) -> Tuple[str, List[Dict[str, str]], List[Dict[str, str]]]:
    """
    Generate answer from Deep Agent and extract web sources and API sources

    Returns:
        Tuple[str, List[Dict[str, str]], List[Dict[str, str]]]: (answer, list of web sources, list of API sources)
    """
    try:
        start_time = time.time()

        result = await agent.ainvoke(
            {"messages": [{"role": "user", "content": prompt}]},
            {"recursion_limit": 30}   # ✅ maksimum step / tool-call döngüsü sınırı
        )

        if not isinstance(result, dict) or "structured_response" not in result:
            logger.error("No structured_response found in result")
            return "", [], []

        structured_data = result["structured_response"]

        data = structured_data.model_dump()

        # Extract answer, web_sources, and api_sources
        answer = data.get("answer", "")
        web_sources = [
            {"name": source.get("name", ""), "url": source.get("url", "")}
            for source in data.get("web_sources", [])
        ]
        api_sources = [
            {
                "name": source.get("name", ""),
                "description": source.get("description", ""),
            }
            for source in data.get("api_sources", [])
        ]

        duration = time.time() - start_time
        llm_duration_seconds.observe(duration)

        return answer, web_sources, api_sources
    except Exception as e:
        logger.error(f"Error in generate_answer: {str(e)}", exc_info=True)
        return f"LLM yanıtı alınamadı: {str(e)}", [], []
