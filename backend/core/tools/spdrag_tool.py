from typing import Any, Dict, List, Tuple
from uuid import uuid4

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import tool
from langgraph.config import get_stream_writer

from backend.core.spdrag import get_compiled_graph
from backend.shared.constants import get_original_user_query, get_selected_files
from backend.shared.logger import get_logger

logger = get_logger("SPDRAG_TOOL")


def _extract_last_ai_message(messages: List[Any]) -> str:
    """Return the last non-empty AIMessage content from a LangGraph message list."""
    for msg in reversed(messages):
        if isinstance(msg, AIMessage):
            content = getattr(msg, "content", "")
            if isinstance(content, list):
                content = "".join(str(part) for part in content)
            if content:
                return str(content)
    return ""


def _build_doc_artifact(selected_files: List[str]) -> List[Dict[str, str]]:
    """Build a doc source artifact from the list of researched files.

    Matches the artifact schema expected by extract_sources_from_artifact in runner.py,
    so the frontend receives the researched document names as sources.
    """
    return [{"name": f, "file": f, "page": ""} for f in selected_files]


@tool(parse_docstring=True, response_format="content_and_artifact")
async def deep_research(query: str) -> Tuple[str, List[Dict[str, str]]]:
    """Perform deep, comprehensive research across all selected local documents.

    Use this when you need to thoroughly investigate a complex question or extract
    detailed information from the selected documents.

    Args:
        query: The research question to investigate.
    """
    selected_files = get_selected_files() or []
    writer = get_stream_writer()

    research_query = get_original_user_query() or query

    if not selected_files:
        logger.warning(
            "deep_research called with no selected documents; synthesis will have no document findings."
        )

    graph = get_compiled_graph()
    thread_id = f"spdrag-tool-{uuid4().hex}"
    config = {"configurable": {"thread_id": thread_id}}
    initial_state = {
        "messages": [HumanMessage(content=research_query)],
        "selected_documents": selected_files,
    }

    logger.info(
        "deep_research invoked: original_query=%r, document_count=%d",
        research_query[:100],
        len(selected_files),
    )

    result = ""

    async for update in graph.astream(initial_state, config=config, stream_mode="updates"):
        if "orchestrator_node" in update:
            for doc_name in selected_files:
                writer({"event": "spdrag_doc_start", "document": doc_name})

        elif "document_sub_agent_node" in update:
            finished = update["document_sub_agent_node"].get("global_context", [])
            for summary in finished:
                writer({"event": "spdrag_doc_end", "document": summary.document_name})

        elif "synthesis_node" in update:
            writer({"event": "spdrag_synthesis_start"})
            messages = update["synthesis_node"].get("messages", [])
            result = _extract_last_ai_message(messages) or result

    if not result:
        result = "SPD-RAG research completed but produced no synthesized output. Try rephrasing your query."

    return result, _build_doc_artifact(selected_files)
