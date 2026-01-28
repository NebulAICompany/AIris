import json
import time
from typing import Tuple, List, Dict, Any, AsyncGenerator
from backend.monitoring.metrics import llm_duration_seconds
from backend.shared.logger import get_logger
from langchain_core.messages import ToolMessage, AIMessageChunk

logger = get_logger("AGENT_RUNNER")


async def generate_answer(
    prompt: str, agent: Any, thread_id: str = None
) -> Tuple[str, List[Dict[str, str]], List[Dict[str, str]], List[Dict[str, str]]]:
    """
    Generate answer from Agent and extract sources from tool artifacts

    Returns:
        Tuple[str, List[Dict], List[Dict], List[Dict]]: (answer, web_sources, api_sources, doc_sources)
    """
    web_sources = []
    api_sources = []
    doc_sources = []

    try:
        start_time = time.time()
        config = {"configurable": {"thread_id": thread_id}} if thread_id else {}
        config["recursion_limit"] = 30

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
        return f"LLM yanıtı alınamadı: {error_str}", [], [], []
    finally:
        web_sources.clear()
        api_sources.clear()
        doc_sources.clear()


async def generate_answer_stream(
    prompt: str, agent: Any, thread_id: str = None
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Stream answer chunks from Agent and extract sources from tool artifacts.

    Yields dicts with keys:
        - "type": "token" | "tool_start" | "tool_end" | "done" | "error"
        - "content": the actual content (for token type)
        - "tool_name": tool name (for tool_start/tool_end types)
        - "sources": dict with web_sources, api_sources, doc_sources (only on "done")
    """
    web_sources = []
    api_sources = []
    doc_sources = []
    last_tool_name = None

    try:
        start_time = time.time()
        config = {"configurable": {"thread_id": thread_id}} if thread_id else {}
        config["recursion_limit"] = 30

        # Use astream with multiple stream modes for token streaming AND updates
        # When using multiple modes, each chunk is (mode_name, data)
        async for stream_chunk in agent.astream(
            {"messages": [{"role": "user", "content": prompt}]},
            config=config,
            stream_mode=["messages", "updates"],
        ):
            # Handle tuple format from multiple stream modes
            if isinstance(stream_chunk, tuple) and len(stream_chunk) == 2:
                mode_name, data = stream_chunk
                
                if mode_name == "messages":
                    # Messages mode: data is (message, metadata) tuple
                    msg = data[0] if isinstance(data, tuple) else data
                    
                    if isinstance(msg, AIMessageChunk):
                        content = msg.content
                        
                        # Handle string content
                        if isinstance(content, str) and content:
                            yield {"type": "token", "content": content}
                        
                        # Handle list content (Anthropic content blocks)
                        elif isinstance(content, list):
                            for block in content:
                                if isinstance(block, dict):
                                    if block.get("type") == "text" and block.get("text"):
                                        yield {"type": "token", "content": block["text"]}
                                    elif block.get("type") == "tool_use":
                                        tool_name = block.get("name", "unknown")
                                        if tool_name != last_tool_name:
                                            yield {"type": "tool_start", "tool_name": tool_name}
                                            last_tool_name = tool_name
                    
                    elif isinstance(msg, ToolMessage):
                        if last_tool_name:
                            yield {"type": "tool_end", "tool_name": last_tool_name}
                            last_tool_name = None
                        
                        # Extract artifacts for sources
                        if hasattr(msg, "artifact") and msg.artifact:
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
                            elif (
                                isinstance(artifact, dict)
                                and "name" in artifact
                                and "description" in artifact
                            ):
                                api_sources.append(artifact)
                
                elif mode_name == "updates":
                    # Updates mode: data is dict with node updates
                    if isinstance(data, dict):
                        for node_name, node_data in data.items():
                            # Check for tool calls in agent node
                            if node_name == "agent" and isinstance(node_data, dict):
                                messages = node_data.get("messages", [])
                                for msg in messages:
                                    if hasattr(msg, "tool_calls") and msg.tool_calls:
                                        for tool_call in msg.tool_calls:
                                            tool_name = tool_call.get("name", "unknown")
                                            if tool_name != last_tool_name:
                                                yield {"type": "tool_start", "tool_name": tool_name}
                                                last_tool_name = tool_name
                            
                            # Check for tool results in tools node
                            elif node_name == "tools" and isinstance(node_data, dict):
                                messages = node_data.get("messages", [])
                                for msg in messages:
                                    if isinstance(msg, ToolMessage):
                                        if last_tool_name:
                                            yield {"type": "tool_end", "tool_name": last_tool_name}
                                            last_tool_name = None
                                        
                                        # Extract artifacts
                                        if hasattr(msg, "artifact") and msg.artifact:
                                            artifact = msg.artifact
                                            if isinstance(artifact, list) and artifact and isinstance(artifact[0], dict):
                                                if "url" in artifact[0]:
                                                    web_sources.extend(artifact)
                                                elif "file" in artifact[0]:
                                                    doc_sources.extend(artifact)
                                            elif isinstance(artifact, dict) and "name" in artifact:
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

        # Final event with sources
        yield {
            "type": "done",
            "sources": {
                "web_sources": web_sources,
                "api_sources": api_sources,
                "doc_sources": doc_sources,
            },
        }

    except Exception as e:
        error_str = str(e)
        if "tool_call_id" in error_str or "tool_calls" in error_str:
            logger.warning(
                "Checkpoint state issue detected. This may be due to incomplete previous conversation state."
            )
        logger.error("Error in generate_answer_stream: %s", error_str, exc_info=True)
        yield {"type": "error", "content": f"LLM yanıtı alınamadı: {error_str}"}
