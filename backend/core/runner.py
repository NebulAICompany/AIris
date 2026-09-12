import json
from typing import Tuple, List, Dict, Any, AsyncGenerator, Optional, Generator
from backend.shared.logger import get_logger
from langchain_core.messages import ToolMessage, AIMessageChunk
from backend.core.checkpointer import clear_thread_checkpoints

logger = get_logger("AGENT_RUNNER")

# Priority list of parameters to extract as query descriptions
QUERY_PARAM_PRIORITY = [
    "query", "content", "file_name", "symbol", "code", "prompt",
    "category_id", "datagroup_code", "serie_codes", "start_date", "end_date"
]


def _has_incomplete_tool_state_error(error_str: str) -> bool:
    """Detect Anthropic/LangGraph errors caused by unresolved checkpointed tool calls."""
    error_lower = error_str.lower()
    return (
        "tool_result blocks immediately after" in error_lower
        or ("tool_use" in error_lower and "tool_result" in error_lower)
        or "tool_call_id" in error_lower
        or "tool_calls" in error_lower
    )


def extract_query_from_args(tool_args: Dict[str, Any], max_length: int = 200) -> Optional[str]:
    """
    Extract a descriptive query string from tool arguments.
    Searches through priority parameters to find a suitable description.
    Used by both StreamProcessor and InnerToolCallbackHandler.
    """
    if not isinstance(tool_args, dict):
        return None
    
    for param in QUERY_PARAM_PRIORITY:
        if param not in tool_args or not tool_args[param]:
            continue
        
        val = tool_args[param]
        if isinstance(val, str) and len(val) > 0:
            return val[:max_length] if len(val) > max_length else val
        elif isinstance(val, (int, float)):
            return str(val)
        elif isinstance(val, list) and len(val) > 0:
            result = str(val)
            return result[:max_length] if len(result) > max_length else result
    
    return None


def extract_text_tokens(content: Any) -> Generator[str, None, None]:
    """
    Extract text content from string or Anthropic-style content blocks.
    Yields text strings suitable for streaming as tokens.
    """
    if isinstance(content, str) and content:
        yield content
    elif isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                text = block.get("text", "")
                if text:
                    yield text


def extract_sources_from_artifact(
    msg: ToolMessage,
    web_sources: List[Dict],
    api_sources: List[Dict],
    doc_sources: List[Dict]
) -> None:
    """
    Extract and categorize sources from a tool message artifact.
    
    Modifies the source lists in place.
    """
    if not hasattr(msg, "artifact") or not msg.artifact:
        return
    
    artifact = msg.artifact
    
    if isinstance(artifact, list) and artifact and isinstance(artifact[0], dict):
        if "url" in artifact[0]:
            web_sources.extend(artifact)
        elif "file" in artifact[0]:
            doc_sources.extend(artifact)
    elif isinstance(artifact, dict) and "name" in artifact and "description" in artifact:
        api_sources.append(artifact)


def deduplicate_sources(sources: List[Dict]) -> List[Dict]:
    """Remove duplicate sources by JSON serialization."""
    return list({json.dumps(s, sort_keys=True): s for s in sources}.values())


class StreamProcessor:
    """
    Processes streaming events from a LangGraph agent.
    
    Handles multiple stream modes (messages, updates, custom) and extracts
    tool events, tokens, and sources in a clean, organized manner.
    """
    
    def __init__(self):
        self.last_tool_name: Optional[str] = None
        self.is_final_response: bool = False
        self.web_sources: List[Dict] = []
        self.api_sources: List[Dict] = []
        self.doc_sources: List[Dict] = []
    
    def _handle_custom_mode(self, data: Dict) -> Generator[Dict, None, None]:
        """Handle custom events from sub-agents via get_stream_writer."""
        if not isinstance(data, dict):
            return
        
        event_type = data.get("event")
        
        if event_type == "inner_tool_start":
            event = {
                "type": "tool_start",
                "tool_name": data.get("tool_name", "unknown"),
                "parent_agent": data.get("agent"),
            }
            query = data.get("query")
            if query:
                event["query"] = query
            yield event

        elif event_type == "inner_tool_end":
            yield {
                "type": "tool_end",
                "tool_name": data.get("tool_name", "unknown"),
                "parent_agent": data.get("agent"),
            }

        elif event_type in ("spdrag_doc_start", "spdrag_doc_end", "spdrag_synthesis_start"):
            event: Dict = {"type": event_type}
            if "document" in data:
                event["document"] = data["document"]
            yield event
    
    def _handle_messages_mode(self, data: Any) -> Generator[Dict, None, None]:
        """Handle messages mode events."""
        msg = data[0] if isinstance(data, tuple) else data
        
        if isinstance(msg, AIMessageChunk):
            if self.is_final_response:
                for text in extract_text_tokens(msg.content):
                    yield {"type": "token", "content": text}
        
        elif isinstance(msg, ToolMessage):
            if self.last_tool_name:
                yield {"type": "tool_end", "tool_name": self.last_tool_name}
                self.last_tool_name = None
            
            extract_sources_from_artifact(
                msg, self.web_sources, self.api_sources, self.doc_sources
            )
    
    def _handle_tool_call(self, tool_call: Any) -> Generator[Dict, None, None]:
        """Process a single tool call and yield tool_start event if needed."""
        if isinstance(tool_call, dict):
            tool_name = tool_call.get("name", "unknown")
            tool_args = tool_call.get("args", {})
        else:
            tool_name = getattr(tool_call, "name", "unknown")
            tool_args = getattr(tool_call, "args", {})
        
        if tool_name == self.last_tool_name:
            return
        
        query = extract_query_from_args(tool_args)
        event = {"type": "tool_start", "tool_name": tool_name, "parent_agent": None}
        if query:
            event["query"] = query
        yield event
        self.last_tool_name = tool_name
    
    def _handle_agent_node(self, node_data: Dict) -> Generator[Dict, None, None]:
        """Handle agent/model node updates."""
        if not isinstance(node_data, dict):
            return
        
        for msg in node_data.get("messages", []):
            has_tool_calls = hasattr(msg, "tool_calls") and bool(msg.tool_calls)
            
            if has_tool_calls:
                self.is_final_response = False
                for tool_call in msg.tool_calls:
                    yield from self._handle_tool_call(tool_call)
            else:
                self.is_final_response = True
                if hasattr(msg, "content") and msg.content:
                    for text in extract_text_tokens(msg.content):
                        yield {"type": "token", "content": text}
    
    def _handle_tools_node(self, node_data: Dict) -> Generator[Dict, None, None]:
        """Handle tools node updates (tool results)."""
        if not isinstance(node_data, dict):
            return
        
        for msg in node_data.get("messages", []):
            if not isinstance(msg, ToolMessage):
                continue
            
            if self.last_tool_name:
                yield {"type": "tool_end", "tool_name": self.last_tool_name}
                self.last_tool_name = None
            
            extract_sources_from_artifact(
                msg, self.web_sources, self.api_sources, self.doc_sources
            )
    
    def _handle_updates_mode(self, data: Dict) -> Generator[Dict, None, None]:
        """Handle updates mode events."""
        if not isinstance(data, dict):
            return
        
        for node_name, node_data in data.items():
            if node_name in ("agent", "model"):
                yield from self._handle_agent_node(node_data)
            elif node_name == "tools":
                yield from self._handle_tools_node(node_data)
    
    def process_chunk(self, stream_chunk: Any) -> Generator[Dict, None, None]:
        """Process a single stream chunk and yield events."""
        if not isinstance(stream_chunk, tuple) or len(stream_chunk) != 2:
            return
        
        mode_name, data = stream_chunk
        
        if mode_name == "custom":
            yield from self._handle_custom_mode(data)
        elif mode_name == "messages":
            yield from self._handle_messages_mode(data)
        elif mode_name == "updates":
            yield from self._handle_updates_mode(data)
    
    def get_deduplicated_sources(self) -> Dict[str, List[Dict]]:
        """Return deduplicated sources."""
        return {
            "web_sources": deduplicate_sources(self.web_sources),
            "api_sources": deduplicate_sources(self.api_sources),
            "doc_sources": deduplicate_sources(self.doc_sources),
        }


async def generate_answer(
    prompt: str, agent: Any, thread_id: str = None
) -> Tuple[str, List[Dict[str, str]], List[Dict[str, str]], List[Dict[str, str]]]:
    """
    Generate answer from Agent and extract sources from tool artifacts.

    Returns:
        Tuple[str, List[Dict], List[Dict], List[Dict]]: (answer, web_sources, api_sources, doc_sources)
    """
    web_sources = []
    api_sources = []
    doc_sources = []

    try:
        for attempt in range(2):
            try:
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
                        if isinstance(msg, ToolMessage):
                            extract_sources_from_artifact(msg, web_sources, api_sources, doc_sources)

                # Deduplicate sources
                web_sources = deduplicate_sources(web_sources)
                api_sources = deduplicate_sources(api_sources)
                doc_sources = deduplicate_sources(doc_sources)

                return answer, web_sources, api_sources, doc_sources
            except Exception as e:
                error_str = str(e)
                if (
                    attempt == 0
                    and thread_id
                    and _has_incomplete_tool_state_error(error_str)
                    and await clear_thread_checkpoints(thread_id)
                ):
                    logger.warning(
                        f"Recovered corrupted checkpoint state for thread_id={thread_id}; retrying generate_answer once."
                    )
                    web_sources = []
                    api_sources = []
                    doc_sources = []
                    continue
                raise
    except Exception as e:
        error_str = str(e)
        if _has_incomplete_tool_state_error(error_str):
            logger.warning(
                "Checkpoint state issue detected. This may be due to incomplete previous conversation state."
            )
        logger.error("Error in generate_answer: %s", error_str, exc_info=True)
        return f"Could not get LLM response: {error_str}", [], [], []


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
    try:
        for attempt in range(2):
            processor = StreamProcessor()
            yielded_any_events = False
            try:
                config = {"configurable": {"thread_id": thread_id}} if thread_id else {}
                config["recursion_limit"] = 30

                async for stream_chunk in agent.astream(
                    {"messages": [{"role": "user", "content": prompt}]},
                    config=config,
                    stream_mode=["messages", "updates", "custom"],
                ):
                    for event in processor.process_chunk(stream_chunk):
                        yielded_any_events = True
                        yield event

                yield {"type": "done", "sources": processor.get_deduplicated_sources()}
                return
            except Exception as e:
                error_str = str(e)
                if (
                    attempt == 0
                    and not yielded_any_events
                    and thread_id
                    and _has_incomplete_tool_state_error(error_str)
                    and await clear_thread_checkpoints(thread_id)
                ):
                    logger.warning(
                        f"Recovered corrupted checkpoint state for thread_id={thread_id}; retrying generate_answer_stream once."
                    )
                    continue
                raise
    except Exception as e:
        error_str = str(e)
        if _has_incomplete_tool_state_error(error_str):
            logger.warning(
                "Checkpoint state issue detected. This may be due to incomplete previous conversation state."
            )
        logger.error("Error in generate_answer_stream: %s", error_str, exc_info=True)
        yield {"type": "error", "content": f"Could not get LLM response: {error_str}"}
