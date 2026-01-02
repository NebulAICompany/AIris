from typing import List, Optional, Dict, Any
from backend.core.runner import generate_answer
from backend.core.agents import create_main_agent, create_news_chat_agent

# Removed upfront retrieval imports - agent will use search_local_documents tool
from backend.security.pii import mask_text, unmask_text
from backend.security.filters import check_openai_moderation
from backend.core.chat import chat_history_manager, MessageRole
from backend.core.tools.visual import get_image_datas, clear_image_datas
from backend.shared.logger import get_logger
from backend.core.tools.finance import get_chart_datas, clear_chart_datas
from backend.core.tools.office import get_generated_files, clear_generated_files
from backend.utils.news import format_news_context

logger = get_logger("QUERY_PIPELINE")


async def run_orchestration(
    query: str,
    web_search_enabled: bool,
    session_id: Optional[str] = None,
    selected_files: Optional[List[str]] = None,
) -> Dict[str, Any]:

    # Clear previous attachments at the start of each new query
    clear_image_datas()
    clear_chart_datas()
    clear_generated_files()

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

    # 4. Agentic RAG: Let the agent decide when to search documents
    # The agent has access to search_local_documents tool and will use it when needed
    logger.info(
        f"🤖 Agentic RAG: Agent will decide when to search documents for query '{query}'"
    )

    agent = create_main_agent(
        web_search_enabled=web_search_enabled,
        conversation_history=conversation_context,
    )
    # Generate initial answer with structured output
    answer, web_sources, api_sources = await generate_answer(
        prompt=masked_query, agent=agent
    )
    # 6. Unmask
    final_answer = unmask_text(answer)

    # 7. Combine document sources with web sources and API sources
    # Note: Document sources will be tracked by the agent when it uses search_local_documents
    all_sources = []
    if selected_files:
        all_sources.extend(selected_files)
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
    answer, web_sources, api_sources = await generate_answer(prompt=query, agent=agent)

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
