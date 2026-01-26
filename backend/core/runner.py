import json
import time
from typing import Tuple, List, Dict, Any
from backend.monitoring.metrics import llm_duration_seconds
from backend.shared.logger import get_logger
from langchain_core.messages import ToolMessage

logger = get_logger("AGENT_RUNNER")


async def generate_answer(
    prompt: str, agent: Any, thread_id: str = None
) -> Tuple[str, List[Dict[str, str]], List[Dict[str, str]], List[Dict[str, str]]]:
    """
    Generate answer from Agent and extract sources from tool artifacts

    Returns:
        Tuple[str, List[Dict], List[Dict], List[Dict]]: (answer, web_sources, api_sources, doc_sources)
    """
    try:
        start_time = time.time()
        config = {"configurable": {"thread_id": thread_id}} if thread_id else {}
        config["recursion_limit"] = 15

        result = await agent.ainvoke(
            {"messages": [{"role": "user", "content": prompt}]}, config=config
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
        error_str = str(e)
        # Check if it's a checkpoint state issue
        if "tool_call_id" in error_str or "tool_calls" in error_str:
            logger.warning(
                "Checkpoint state issue detected. This may be due to incomplete previous conversation state."
            )
        # Use % formatting to avoid KeyError with curly braces in error messages
        logger.error("Error in generate_answer: %s", error_str, exc_info=True)
        return f"LLM yanıtı alınamadı: {error_str}", [], []
    finally:
        web_sources.clear()
        api_sources.clear()
        doc_sources.clear()
