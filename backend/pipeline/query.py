from typing import List, Optional, Dict, Any, AsyncGenerator
import json
from uuid import uuid4
from langchain_core.messages import AIMessage, HumanMessage
from backend.core.runner import generate_answer, generate_answer_stream
from backend.core.agents import create_main_agent, create_news_chat_agent
from backend.core.spdrag import get_compiled_graph
from backend.security.pii import mask_text, unmask_text
from backend.security.filters import check_openai_moderation
from backend.core.chat import chat_history_manager, MessageRole
from backend.core.tools.visual import get_image_datas, clear_image_datas
from backend.shared.logger import get_logger
from backend.core.tools.finance import get_chart_datas, clear_chart_datas
from backend.core.tools.office import get_generated_files, clear_generated_files
from backend.utils.news import format_news_context
from backend.shared.constants import set_selected_files, set_original_user_query

logger = get_logger("QUERY_PIPELINE")


def _extract_last_ai_message_content(messages: List[Any]) -> str:
    """Extract the last AI message content from a LangGraph state message list."""
    for msg in reversed(messages):
        if isinstance(msg, AIMessage):
            content = getattr(msg, "content", "")
            if isinstance(content, list):
                content = "".join(str(part) for part in content)
            if content:
                return str(content)
    return ""


def _build_spdrag_messages(
    masked_query: str,
    session_id: Optional[str],
    max_messages: int = 20,
) -> List[Any]:
    """Build SPD-RAG message history in LangChain message format."""
    if not session_id:
        return [HumanMessage(content=masked_query)]

    session = chat_history_manager.get_session(session_id)
    if not session or not session.messages:
        return [HumanMessage(content=masked_query)]

    lc_messages: List[Any] = []
    recent_messages = session.messages[-max_messages:]
    last_index = len(recent_messages) - 1

    for idx, chat_msg in enumerate(recent_messages):
        role = chat_msg.role
        content = chat_msg.content

        if role == MessageRole.USER:
            # Always send the current turn in masked form.
            if idx == last_index:
                content = masked_query
            lc_messages.append(HumanMessage(content=content))
        elif role == MessageRole.ASSISTANT:
            lc_messages.append(AIMessage(content=content))

    if not lc_messages or not isinstance(lc_messages[-1], HumanMessage):
        lc_messages.append(HumanMessage(content=masked_query))

    return lc_messages


async def _run_spdrag_orchestration(
    masked_query: str,
    session_id: Optional[str],
    selected_files: Optional[List[str]],
) -> Dict[str, Any]:
    """Run SPD-RAG graph and normalize output to the existing response contract."""
    graph = get_compiled_graph()
    # SPD-RAG runs are request-scoped to avoid stale checkpoint state bleed-over.
    base_thread_id = session_id or "spdrag-default-session"
    thread_id = f"{base_thread_id}-spdrag-{uuid4().hex}"
    graph_config = {"configurable": {"thread_id": thread_id}}
    messages = _build_spdrag_messages(masked_query=masked_query, session_id=session_id)
    initial_state: Dict[str, Any] = {
        "messages": messages,
        "selected_documents": selected_files or [],
    }

    state = await graph.ainvoke(initial_state, config=graph_config)
    final_answer = _extract_last_ai_message_content(state.get("messages", []))
    final_answer = unmask_text(final_answer) if final_answer else ""
    if not final_answer:
        final_answer = (
            "SPD-RAG pipeline completed but returned no content. "
            "Please try rephrasing your request."
        )

    images = get_image_datas()
    charts = get_chart_datas()
    generated_files = get_generated_files()
    sources: List[str] = []

    metadata: Dict[str, Any] = {}
    if images:
        metadata["images"] = images
    if charts:
        metadata["charts"] = charts
    if generated_files:
        metadata["generatedFiles"] = generated_files
    if sources:
        metadata["sources"] = sources

    chat_history_manager.add_message(
        session_id,
        MessageRole.ASSISTANT,
        final_answer,
        metadata if metadata else None,
    )

    return {
        "response": final_answer,
        "images": images,
        "charts": charts,
        "generatedFiles": generated_files,
        "sources": sources,
        "session_id": session_id,
    }


async def run_orchestration(
    query: str,
    web_search_enabled: bool,
    use_spdrag: bool = False,
    session_id: Optional[str] = None,
    selected_files: Optional[List[str]] = None,
) -> Dict[str, Any]:
    # Clear previous attachments at the start of each new query
    clear_image_datas()
    clear_chart_datas()
    clear_generated_files()

    # Set global selected files for RAG queries
    set_selected_files(selected_files)

    # Set global original user query for RAG queries
    set_original_user_query(query)

    # Add user message to chat history
    chat_history_manager.add_message(session_id, MessageRole.USER, query)

    # Reduce history if too long
    session = chat_history_manager.get_session(session_id)
    if session and len(session.messages) > 30:
        chat_history_manager.reduce_history(session, target_messages=20)

    # 1. Input moderation (OpenAI moderation)
    input_moderation = check_openai_moderation(query)
    if input_moderation["flagged"]:
        response_message = f"Your query contains inappropriate content: {input_moderation['violations']}"

        # Add assistant response to chat history
        chat_history_manager.add_message(
            session_id, MessageRole.ASSISTANT, response_message
        )

        return {
            "response": response_message,
            "images": [],
            "charts": [],
            "generatedFiles": [],
        }

    # 2. Mask sensitive information
    masked_query_list = await mask_text([query], "query")
    masked_query = masked_query_list[0]

    if use_spdrag:
        logger.info("🚀 SPD-RAG mode enabled for synchronous query orchestration")
        return await _run_spdrag_orchestration(
            masked_query=masked_query,
            session_id=session_id,
            selected_files=selected_files,
        )

    # 4. Agentic RAG: Let the agent decide when to search documents
    # The agent has access to search_local_documents tool and will use it when needed
    logger.info(
        f"🤖 Agentic RAG: Agent will decide when to search documents for query '{query}'"
    )

    agent = create_main_agent(
        web_search_enabled=web_search_enabled,
    )
    # Generate initial answer with structured output
    answer, web_sources, api_sources, doc_sources = await generate_answer(
        prompt=masked_query, agent=agent, thread_id=session_id
    )
    # 6. Unmask
    final_answer = unmask_text(answer)

    # 7. Combine document sources with web sources and API sources
    all_sources = []

    # Add document sources from RAG tool artifacts
    for doc_source in doc_sources:
        name = doc_source.get("name", "")
        file_name = doc_source.get("file", "")
        if name and file_name:
            all_sources.append(f"{name}|doc://{file_name}")
    for web_source in web_sources:
        # Format as "Name|URL" for frontend to parse and display as clickable link
        name = web_source.get("name", "")
        url = web_source.get("url", "")
        if name and url:
            all_sources.append(f"{name}|{url}")
    for api_source in api_sources:
        # Format API sources as "API Name|description" (no URL, but frontend can handle it)
        name = api_source.get("name", "")
        description = api_source.get("description", "")
        if name:
            # Use description as a pseudo-URL for consistency, or just name
            display_text = f"{name}" + (f" - {description}" if description else "")
            all_sources.append(f"{display_text}|api://{name}")

    # 9. Get images, charts, and generated files and add assistant response to chat history
    images = get_image_datas()
    charts = get_chart_datas()
    generated_files = get_generated_files()

    metadata = {}
    if images:
        metadata["images"] = images
    if charts:
        metadata["charts"] = charts
    if generated_files:
        metadata["generatedFiles"] = generated_files
    if all_sources:
        metadata["sources"] = all_sources

    metadata = metadata if metadata else None
    chat_history_manager.add_message(
        session_id, MessageRole.ASSISTANT, final_answer, metadata
    )

    return {
        "response": final_answer,
        "images": images,
        "charts": charts,
        "generatedFiles": generated_files,
        "sources": all_sources,
    }


async def run_news_chat_orchestration(
    query: str,
    news_context: dict,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Specialized orchestration for news chat queries with news context and web search.
    """

    # Handle chat history and session management
    if session_id:
        # Add user message to chat history
        chat_history_manager.add_message(session_id, MessageRole.USER, query)

        # Get conversation context
        conversation_context = chat_history_manager.get_conversation_context(
            session_id, max_messages=10
        )

        # Reduce history if too long
        session = chat_history_manager.get_session(session_id)
        if session and len(session.messages) > 30:
            chat_history_manager.reduce_history(session, target_messages=20)
    else:
        conversation_context = []

    # Create news context string
    news_context_str = format_news_context(news_context)

    # Create specialized news agent
    agent = create_news_chat_agent(
        news_context=news_context_str,
        conversation_history=conversation_context,
    )

    # Generate answer
    answer, web_sources, api_sources, doc_sources = await generate_answer(
        prompt=query, agent=agent
    )

    # Combine web sources and API sources
    all_sources = []
    for web_source in web_sources:
        name = web_source.get("name", "")
        url = web_source.get("url", "")
        if name and url:
            all_sources.append(f"{name}|{url}")
    for api_source in api_sources:
        name = api_source.get("name", "")
        description = api_source.get("description", "")
        if name:
            display_text = f"{name}" + (f" - {description}" if description else "")
            all_sources.append(f"{display_text}|api://{name}")

    # Get images
    images = get_image_datas()

    # Add assistant response to chat history
    if session_id:
        metadata = {"images": images} if images else None
        chat_history_manager.add_message(
            session_id, MessageRole.ASSISTANT, answer, metadata
        )

    return {"response": answer, "images": images, "session_id": session_id}


async def run_orchestration_stream(
    query: str,
    web_search_enabled: bool,
    use_spdrag: bool = False,
    session_id: Optional[str] = None,
    selected_files: Optional[List[str]] = None,
) -> AsyncGenerator[str, None]:
    """
    Streaming version of run_orchestration using Server-Sent Events format.

    Yields SSE-formatted strings with events:
        - token: text chunk from the LLM
        - tool_start: tool is being called
        - tool_end: tool call completed
        - done: final event with sources, images, charts, files
        - error: error occurred
    """
    # Clear previous attachments at the start of each new query
    clear_image_datas()
    clear_chart_datas()
    clear_generated_files()

    # Set global selected files for RAG queries
    set_selected_files(selected_files)

    # Set global original user query for RAG queries
    set_original_user_query(query)

    # Add user message to chat history
    chat_history_manager.add_message(session_id, MessageRole.USER, query)

    # Reduce history if too long
    session = chat_history_manager.get_session(session_id)
    if session and len(session.messages) > 30:
        chat_history_manager.reduce_history(session, target_messages=20)

    # 1. Input moderation (OpenAI moderation)
    input_moderation = check_openai_moderation(query)
    if input_moderation["flagged"]:
        response_message = f"Your query contains inappropriate content: {input_moderation['violations']}"
        chat_history_manager.add_message(
            session_id, MessageRole.ASSISTANT, response_message
        )
        yield f"data: {json.dumps({'type': 'error', 'content': response_message})}\n\n"
        return

    # 2. Mask sensitive information
    masked_query_list = await mask_text([query], "query")
    masked_query = masked_query_list[0]

    if use_spdrag:
        logger.info(
            "SPD-RAG mode enabled for streaming query orchestration (selected_files count=%s)",
            len(selected_files) if selected_files else 0,
        )
        if selected_files:
            logger.info("SPD-RAG selected documents: %s", selected_files)
        else:
            logger.warning(
                "SPD-RAG selected_files is empty or None; fan-out will skip and synthesis will use no documents."
            )
        spdrag_result = await _run_spdrag_orchestration(
            masked_query=masked_query,
            session_id=session_id,
            selected_files=selected_files,
        )

        if spdrag_result["response"]:
            yield f"data: {json.dumps({'type': 'token', 'content': spdrag_result['response']})}\n\n"

        yield (
            "data: "
            + json.dumps(
                {
                    "type": "done",
                    "content": spdrag_result["response"],
                    "images": spdrag_result["images"],
                    "charts": spdrag_result["charts"],
                    "generatedFiles": spdrag_result["generatedFiles"],
                    "sources": spdrag_result["sources"],
                    "tools": [],
                }
            )
            + "\n\n"
        )
        return

    logger.info(
        f"🤖 Agentic RAG (Streaming): Agent will decide when to search documents for query '{query}'"
    )

    agent = create_main_agent(
        web_search_enabled=web_search_enabled,
    )

    # Accumulate full answer for chat history
    full_answer = ""
    all_sources = []
    all_tools = []  # Track tools used during streaming

    # Stream the response
    async for chunk in generate_answer_stream(
        prompt=masked_query, agent=agent, thread_id=session_id
    ):
        if chunk["type"] == "token":
            full_answer += chunk["content"]
            yield f"data: {json.dumps({'type': 'token', 'content': chunk['content']})}\n\n"

        elif chunk["type"] == "tool_start":
            tool_info = {
                "tool_name": chunk["tool_name"],
                "parent_agent": chunk.get("parent_agent"),
                "query": chunk.get("query"),
            }
            all_tools.append(tool_info)

            event_data = {
                "type": "tool_start",
                **tool_info,
            }
            yield f"data: {json.dumps(event_data)}\n\n"

        elif chunk["type"] == "tool_end":
            event_data = {
                "type": "tool_end",
                "tool_name": chunk["tool_name"],
                "parent_agent": chunk.get("parent_agent"),
            }
            yield f"data: {json.dumps(event_data)}\n\n"

        elif chunk["type"] == "error":
            yield f"data: {json.dumps({'type': 'error', 'content': chunk['content']})}\n\n"
            return

        elif chunk["type"] == "done":
            # Process sources
            sources = chunk.get("sources", {})
            web_sources = sources.get("web_sources", [])
            api_sources = sources.get("api_sources", [])
            doc_sources = sources.get("doc_sources", [])

            # Format sources
            for doc_source in doc_sources:
                name = doc_source.get("name", "")
                file_name = doc_source.get("file", "")
                if name and file_name:
                    all_sources.append(f"{name}|doc://{file_name}")
            for web_source in web_sources:
                name = web_source.get("name", "")
                url = web_source.get("url", "")
                if name and url:
                    all_sources.append(f"{name}|{url}")
            for api_source in api_sources:
                name = api_source.get("name", "")
                description = api_source.get("description", "")
                if name:
                    display_text = f"{name}" + (
                        f" - {description}" if description else ""
                    )
                    all_sources.append(f"{display_text}|api://{name}")

            # Get images, charts, and generated files
            images = get_image_datas()
            charts = get_chart_datas()
            generated_files = get_generated_files()

            # Unmask the full answer
            final_answer = unmask_text(full_answer)

            # Save to chat history
            metadata = {}
            if images:
                metadata["images"] = images
            if charts:
                metadata["charts"] = charts
            if generated_files:
                metadata["generatedFiles"] = generated_files
            if all_sources:
                metadata["sources"] = all_sources
            if all_tools:
                metadata["tools"] = all_tools

            metadata = metadata if metadata else None
            chat_history_manager.add_message(
                session_id, MessageRole.ASSISTANT, final_answer, metadata
            )

            yield f"data: {json.dumps({'type': 'done', 'content': final_answer, 'images': images, 'charts': charts, 'generatedFiles': generated_files, 'sources': all_sources, 'tools': all_tools})}\n\n"
