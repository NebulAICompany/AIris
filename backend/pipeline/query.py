from typing import List, Optional, Dict, Any
from backend.retrieval.reranker import rerank
from backend.core.runner import generate_answer
from backend.core.agents import create_main_agent, create_news_chat_agent
from backend.retrieval.retriever import (
    load_vectorstore,
    retrieve_with_keyword_helping,
)
from backend.security.pii import mask_text, unmask_text
from backend.security.filters import check_openai_moderation
from backend.utils.query import (
    refine_query,
)
from backend.core.chat import chat_history_manager, MessageRole
from backend.shared.constants import VECTORSTORE_PATH_STR
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

    client = load_vectorstore(VECTORSTORE_PATH_STR)

    # 0. Selected files check - skip retrieval if no files selected
    skip_retrieval = not selected_files or len(selected_files) == 0

    # 1. Preprocessing and analysis
    refined_result = refine_query(query)
    preprocessed_query = refined_result.refined_query
    query_keywords = refined_result.keywords

    # 2. Input moderation (OpenAI moderation)
    input_moderation = check_openai_moderation(preprocessed_query)
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

    # 3. Mask sensitive information
    masked_query_list = await mask_text([preprocessed_query], "query")
    masked_query = masked_query_list[0]

    # 4. Enhanced Retrieval using vector + keyword helping
    reranked_docs = None
    unique_file_names = []

    if skip_retrieval:
        reranked_docs = []
        logger.info(
            f"📄 No documents used in retrieval for query '{query}' (no files selected)"
        )
    else:
        preprocessed_query = preprocessed_query + " Selected Files: " + ", ".join(selected_files)
        retrieved_docs = retrieve_with_keyword_helping(
            client=client,
            query=preprocessed_query,
            query_terms=query_keywords,
            k=15,
            selected_files=selected_files,
        )

        if retrieved_docs:
            # Extract only the content from the retrieved docs before reranking
            doc_contents = [
                {"content": doc["content"], "metadata": doc["metadata"]}
                for doc in retrieved_docs
            ]
            reranked_docs = rerank(
                preprocessed_query, doc_contents, with_score=False, top_n=5
            )

            if reranked_docs:
                unique_file_names_set = set()
                for doc in reranked_docs:
                    file_name = doc.get("metadata", {}).get("file_name")
                    if file_name:
                        unique_file_names_set.add(file_name)

                unique_file_names = sorted(list(unique_file_names_set))
    context_entries = []

    if reranked_docs:
        for doc in reranked_docs:
            content = doc["content"]
            metadata = doc["metadata"]
            metadata_str = ""
            metadata_str += f"Source: {metadata.get('file_name')}\n"
            context_entries.append(
                f"Local Content: {content}\n\n Local Metadata:\n{metadata_str}"
            )

        local_context = "\n\n---\n\n".join(context_entries)
    else:
        # Determine the reason for empty context and provide appropriate message
        if skip_retrieval:
            local_context = "Local Content Status: No content could be retrieved from local documents because no files were selected."
        else:
            local_context = "Local Content Status: No relevant content could be found for your query in the selected files."

    agent = create_main_agent(
        local_context=local_context,
        web_search_enabled=web_search_enabled,
        query=masked_query,
        conversation_history=conversation_context,
    )
    # Generate initial answer
    answer = await generate_answer(prompt=masked_query, agent=agent)
    # 6. Unmask
    final_answer = unmask_text(answer)

    # 7. Get images, charts, and generated files and add assistant response to chat history
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
    if unique_file_names:
        metadata["sources"] = unique_file_names

    metadata = metadata if metadata else None
    chat_history_manager.add_message(
        session_id, MessageRole.ASSISTANT, final_answer, metadata
    )

    return {
        "response": final_answer,
        "images": images,
        "charts": charts,
        "generatedFiles": generated_files,
        "sources": unique_file_names,
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
        query=query,
        conversation_history=conversation_context,
    )

    # Generate answer
    answer = await generate_answer(prompt=query, agent=agent)

    # Get images
    images = get_image_datas()

    # Add assistant response to chat history
    if session_id:
        metadata = {"images": images} if images else None
        chat_history_manager.add_message(
            session_id, MessageRole.ASSISTANT, answer, metadata
        )

    return {"response": answer, "images": images, "session_id": session_id}
