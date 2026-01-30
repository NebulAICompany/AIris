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
    Uses astream with multiple modes for clean main agent streaming.

    Yields dicts with keys:
        - "type": "token" | "tool_start" | "tool_end" | "done" | "error"
        - "content": the actual content (for token type)
        - "tool_name": tool name (for tool_start/tool_end types)
        - "sources": dict with web_sources, api_sources, doc_sources (only on "done")
    """
    web_sources = []
    api_sources = []
    doc_sources = []

    try:
        start_time = time.time()
        config = {"configurable": {"thread_id": thread_id}} if thread_id else {}
        config["recursion_limit"] = 30

        # Use astream with multiple modes:
        # - "messages": streams main agent's message tokens (not nested sub-agents)
        # - "updates": gives us tool call events from all levels
        # - "custom": receives custom events from sub-agents via get_stream_writer
        last_tool_name = None
        current_inner_tool = None
        # Track whether we're in the final response phase (no more tool calls)
        # Only stream tokens when this is True to avoid showing agent's thinking
        is_final_response = False
        
        async for stream_chunk in agent.astream(
            {"messages": [{"role": "user", "content": prompt}]},
            config=config,
            stream_mode=["messages", "updates", "custom"],
        ):
            # Handle tuple format from multiple stream modes: (mode_name, data)
            if isinstance(stream_chunk, tuple) and len(stream_chunk) == 2:
                mode_name, data = stream_chunk
                
                if mode_name == "custom":
                    # Custom events from sub-agents via get_stream_writer
                    if isinstance(data, dict):
                        event_type = data.get("event")
                        
                        if event_type == "subagent_start":
                            # A sub-agent has started
                            logger.debug(f"Subagent started: {data.get('agent')}")
                        
                        elif event_type == "inner_tool_start":
                            # An inner tool within a sub-agent has started
                            tool_name = data.get("tool_name", "unknown")
                            parent_agent = data.get("agent")
                            query = data.get("query")
                            current_inner_tool = tool_name
                            logger.debug(f"[custom] Received inner_tool_start: {tool_name}, query: {query[:50] if query else 'None'}...")
                            event = {
                                "type": "tool_start",
                                "tool_name": tool_name,
                                "parent_agent": parent_agent,
                            }
                            if query:
                                event["query"] = query
                            yield event
                        
                        elif event_type == "inner_tool_end":
                            # An inner tool within a sub-agent has completed
                            tool_name = data.get("tool_name", "unknown")
                            parent_agent = data.get("agent")
                            current_inner_tool = None
                            logger.debug(f"[custom] Received inner_tool_end: {tool_name}")
                            yield {
                                "type": "tool_end",
                                "tool_name": tool_name,
                                "parent_agent": parent_agent,
                            }
                        
                        elif event_type == "subagent_end":
                            # A sub-agent has finished
                            logger.debug(f"Subagent ended: {data.get('agent')}")
                
                elif mode_name == "messages":
                    # Messages mode: data is (message, metadata) tuple
                    msg = data[0] if isinstance(data, tuple) else data
                    
                    if isinstance(msg, AIMessageChunk):
                        content = msg.content
                        
                        # Only stream tokens when in final response phase
                        # (after agent has finished calling tools)
                        if is_final_response:
                            # Handle string content
                            if isinstance(content, str) and content:
                                yield {"type": "token", "content": content}
                            
                            # Handle list content (Anthropic content blocks)
                            elif isinstance(content, list):
                                for block in content:
                                    if isinstance(block, dict):
                                        if block.get("type") == "text" and block.get("text"):
                                            yield {"type": "token", "content": block["text"]}
                        else:
                            # Check for tool_use blocks (agent is still thinking/calling tools)
                            if isinstance(content, list):
                                for block in content:
                                    if isinstance(block, dict) and block.get("type") == "tool_use":
                                        tool_name = block.get("name", "unknown")
                                        logger.debug(f"[messages] tool_use block detected: {tool_name} (skipping - will use updates mode)")
                    
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
                        # Debug: log all nodes in updates
                        logger.debug(f"[updates] Nodes in update: {list(data.keys())}")
                        for node_name, node_data in data.items():
                            # Check for tool calls in agent or model node
                            # (LangGraph uses "agent" for react agents, but "model" for other setups)
                            if node_name in ("agent", "model") and isinstance(node_data, dict):
                                messages = node_data.get("messages", [])
                                logger.debug(f"[updates] {node_name} node has {len(messages)} messages")
                                for msg in messages:
                                    has_tool_calls = hasattr(msg, "tool_calls") and bool(msg.tool_calls)
                                    logger.debug(f"[updates] Message type: {type(msg).__name__}, has_tool_calls: {has_tool_calls}")
                                    
                                    if has_tool_calls:
                                        # Agent is calling tools - not final response yet
                                        is_final_response = False
                                        for tool_call in msg.tool_calls:
                                            # tool_call can be dict or object
                                            if isinstance(tool_call, dict):
                                                tool_name = tool_call.get("name", "unknown")
                                                tool_args = tool_call.get("args", {})
                                            else:
                                                tool_name = getattr(tool_call, "name", "unknown")
                                                tool_args = getattr(tool_call, "args", {})
                                            
                                            logger.debug(f"[updates] Tool call: {tool_name}, args type: {type(tool_args)}, args keys: {list(tool_args.keys()) if isinstance(tool_args, dict) else 'N/A'}, args: {str(tool_args)[:150]}")
                                            
                                            if tool_name != last_tool_name:
                                                # Extract descriptive parameter from tool args
                                                query = None
                                                if isinstance(tool_args, dict):
                                                    # Priority list of parameters to look for
                                                    for param in ["query", "content", "file_name", "symbol", "code", "prompt"]:
                                                        if param in tool_args and tool_args[param]:
                                                            val = tool_args[param]
                                                            if isinstance(val, str) and len(val) > 0:
                                                                query = val
                                                                break
                                                
                                                logger.debug(f"[updates] Yielding tool_start: {tool_name}, query={query[:50] if query else 'None'}...")
                                                event = {"type": "tool_start", "tool_name": tool_name, "parent_agent": None}
                                                if query:
                                                    event["query"] = query[:200] if len(query) > 200 else query
                                                yield event
                                                last_tool_name = tool_name
                                    else:
                                        # No tool calls - this is the final response
                                        # Extract and yield the content directly from updates mode
                                        # (more reliable than messages mode which streams before we know if tool calls are coming)
                                        is_final_response = True
                                        logger.debug("[updates] No tool calls - yielding final response content")
                                        
                                        # Extract content from the message
                                        if hasattr(msg, "content") and msg.content:
                                            content = msg.content
                                            if isinstance(content, str) and content:
                                                yield {"type": "token", "content": content}
                                            elif isinstance(content, list):
                                                for block in content:
                                                    if isinstance(block, dict) and block.get("type") == "text":
                                                        text = block.get("text", "")
                                                        if text:
                                                            yield {"type": "token", "content": text}
                            
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
