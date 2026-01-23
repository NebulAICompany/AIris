import json
import time
from typing import Tuple, List, Dict, Any
from backend.monitoring.metrics import llm_duration_seconds
from backend.shared.logger import get_logger
from langchain_core.messages import ToolMessage

logger = get_logger("AGENT_RUNNER")


async def generate_answer(
    prompt: str, agent: Any
) -> Tuple[str, List[Dict[str, str]], List[Dict[str, str]], List[Dict[str, str]]]:
    """
    Generate answer from Deep Agent and extract sources from tool artifacts

    Returns:
        Tuple[str, List[Dict], List[Dict], List[Dict]]: (answer, web_sources, api_sources, doc_sources)
    """
    try:
        start_time = time.time()

        result = await agent.ainvoke(
            {"messages": [{"role": "user", "content": prompt}]}
        )

        # Extract answer from the last AI message
        answer = ""
        if "messages" in result and result["messages"]:
            for msg in reversed(result["messages"]):
                if hasattr(msg, "content") and msg.content:
                    answer = msg.content
                    break

        # Extract sources from tool artifacts
        web_sources = []
        api_sources = []
        doc_sources = []

        if "messages" in result:
            for msg in result["messages"]:
                if (
                    not isinstance(msg, ToolMessage)
                    or not hasattr(msg, "artifact")
                    or not msg.artifact
                ):
                    continue

                artifact = msg.artifact

                if (
                    isinstance(artifact, list)
                    and artifact
                    and isinstance(artifact[0], dict)
                ):
                    if "url" in artifact[0]:
                        web_sources.extend(artifact)
                    elif "file" in artifact[0]:
                        doc_sources.extend(artifact)

                # Handle dict artifacts (API sources)
                elif (
                    isinstance(artifact, dict)
                    and "name" in artifact
                    and "description" in artifact
                ):
                    api_sources.append(artifact)

        # Deduplicate sources
        web_sources = list(
            {json.dumps(s, sort_keys=True): s for s in web_sources}.values()
        )
        api_sources = list(
            {json.dumps(s, sort_keys=True): s for s in api_sources}.values()
        )
        doc_sources = list(
            {json.dumps(s, sort_keys=True): s for s in doc_sources}.values()
        )

        duration = time.time() - start_time
        llm_duration_seconds.observe(duration)

        return answer, web_sources, api_sources, doc_sources
    except Exception as e:
        logger.error(f"Error in generate_answer: {str(e)}", exc_info=True)
        return f"LLM yanıtı alınamadı: {str(e)}", [], [], []
