from typing import List, Optional
from backend.retrieval.reranker import rerank
from backend.core.runner import generate_answer
from backend.core.agents import create_rag_agent
from backend.retrieval.retriever import retrieve_top_k, load_vectorstore
from backend.security.pii import mask_text, unmask_text
from backend.security.filters import check_openai_moderation
from backend.utils.query import reflect_and_retry, extract_image_references_from_context, load_images_from_paths, spell_check, detect_language, filter_docs_by_selected_files
from backend.core.chat import chat_history_manager, MessageRole
from backend.shared.constants import VECTORSTORE_PATH
from backend.shared.logger import get_logger
import os

logger = get_logger("QUERY_PIPELINE")

def preprocess_query(query: str):
    lang = detect_language(query)
    logger.debug(f"Detected Language: {lang}")
    if lang=="Turkish":
        corrected = spell_check(query)
        return corrected, lang
    return query, lang


async def run_orchestration(
    query: str,
    web_search_enabled: bool,
    pre_embedding_process: str = "none",
    session_id: Optional[str] = None,
    selected_files: Optional[List[str]] = None,
) -> str:

    logger.info(f"🔍 Query Orchestrator started:")
    logger.info(f"   - Query: {query}")
    logger.info(f"   - Web Search Enabled: {web_search_enabled}")
    logger.info(f"   - Pre-embedding Process: {pre_embedding_process}")
    logger.info(f"   - Session ID: {session_id}")
    logger.info(f"   - Selected Files: {selected_files}")


    # Handle chat history and session management
    if session_id:
        # Add user message to chat history
        chat_history_manager.add_message(session_id, MessageRole.USER, query)

        # Get conversation context
        conversation_context = chat_history_manager.get_conversation_context(
            session_id, max_messages=10
        )
        logger.debug(f"   - Conversation context: {len(conversation_context)} messages")

        # Reduce history if too long
        session = chat_history_manager.get_session(session_id)
        if session and len(session.messages) > 30:
            logger.info(f"   - Reducing chat history from {len(session.messages)} messages")
            chat_history_manager.reduce_history(session, target_messages=20)
    else:
        conversation_context = []
        logger.debug(f"   - No session ID provided, processing as standalone query")

    if os.path.exists(f"{VECTORSTORE_PATH}/index.faiss"):
        logger.info(f"Loading vectorstore from {VECTORSTORE_PATH}")
        if pre_embedding_process == "cch":
            logger.info(
                "   - Contextual Chunk Headers (CCH) enhanced chunks will be used for retrieval"
            )
        else:
            logger.info("   - Standard chunks will be used for retrieval")
        load_vectorstore(VECTORSTORE_PATH)

    # 1. Temizlik + analiz
    preprocessed_query, lang = preprocess_query(query)

    # 2. Girdi kontrolü (OpenAI moderation)
    input_moderation = check_openai_moderation(preprocessed_query)
    if input_moderation["flagged"]:
        return f"Sorgunuz uygunsuz içerikler içeriyor: {input_moderation['violations']}"

    # 3. Hassas bilgileri maskele
    masked_query = mask_text(preprocessed_query)
    logger.debug(f"Masked Query: {masked_query}")

    ENABLED_RAG_TECHNIQUES = ["rse"]

    if "rag_fusion" in ENABLED_RAG_TECHNIQUES:
        # 4. Enhanced Retrieval with RAG Fusion (Multiple Query Generation + RRF)
        from backend.retrieval.rag_fusion import retrieve_with_fusion

        fusion_docs, fusion_metadata = await retrieve_with_fusion(
            preprocessed_query, k=15, num_queries=4, top_n=5, final_rerank=True, excessive_k=60
        )

        if not fusion_docs:
            return "Üzgünüm, sorgunuzla ilgili belgede bilgi bulamadım."

        logger.debug(f"🔀 RAG Fusion Results: {fusion_metadata}")

        # Filter fusion docs by selected files
        filtered_fusion_docs = filter_docs_by_selected_files(
            fusion_docs, selected_files
        )

        if not filtered_fusion_docs:
            if selected_files:
                return f"Üzgünüm, seçilen dosyalarda ({', '.join(selected_files)}) sorgunuzla ilgili bilgi bulamadım."
            else:
                return "Üzgünüm, sorgunuzla ilgili belgede bilgi bulamadım."

        # Use filtered fusion docs directly (they're already optimized and reranked)
        reranked_docs = filtered_fusion_docs
    elif "rse" in ENABLED_RAG_TECHNIQUES:
        # 4. Enhanced Retrieval with RSE (Relevant Segment Extraction)
        from backend.retrieval.rse import retrieve_with_rse

        rse_chunks, rse_scores = retrieve_with_rse(
            preprocessed_query, k=15
        )

        if not rse_chunks:
            return "Üzgünüm, sorgunuzla ilgili belgede bilgi bulamadım."
        # logger.debug(f"RSE Chunks: {rse_chunks[0]}\n RSE Scores: {rse_scores[0]}")

        # Filter RSE chunks by selected files
        filtered_rse_chunks = filter_docs_by_selected_files(rse_chunks, selected_files)

        if not filtered_rse_chunks:
            if selected_files:
                return f"Üzgünüm, seçilen dosyalarda ({', '.join(selected_files)}) sorgunuzla ilgili bilgi bulamadı."
            else:
                return "Üzgünüm, sorgunuzla ilgili belgede bilgi bulamadım."

        # Use filtered RSE-enhanced chunks directly (they're already optimized)
        reranked_docs = filtered_rse_chunks[:5]  # Take top 5 RSE segments
    else:
        # 4. Enhanced Retrieval + Reranking 
        retrieved_docs = retrieve_top_k(
            preprocessed_query, k=15
        )  # Get more docs for better reranking

        if not retrieved_docs:
            return "Üzgünüm, sorgunızla ilgili belgede bilgi bulamadı."

        # Filter retrieved docs by selected files
        filtered_retrieved_docs = filter_docs_by_selected_files(
            retrieved_docs, selected_files
        )

        if not filtered_retrieved_docs:
            if selected_files:
                return f"Üzgünüm, seçilen dosyalarda ({', '.join(selected_files)}) sorgunuzla ilgili bilgi bulamadı."
            else:
                return "Üzgünüm, sorgunuzla ilgili belgede bilgi bulamadı."

        # Extract only the content from the filtered retrieved docs before reranking
        doc_contents = [
            {"content": doc["content"], "metadata": doc["metadata"]}
            for doc in filtered_retrieved_docs
        ]
        reranked_docs = rerank(
            preprocessed_query, doc_contents, with_score=False, top_n=5
        )

    context_entries = []

    for doc in reranked_docs:
        content = doc["content"]
        metadata = doc["metadata"]

        metadata_str = ""
        metadata_str += f"Source: {metadata.get('file_name')}\n"

        context_entries.append(
            f"Lokal İçerik: {content}\n\n Lokal Metadata:\n{metadata_str}"
        )

    local_context = "\n\n---\n\n".join(context_entries)
    logger.debug(f"   - Local Context: {local_context}")
    logger.debug("using web search ?= ", web_search_enabled)

    cleaned_context, image_paths = extract_image_references_from_context(local_context)

    image_datas = load_images_from_paths(image_paths)

    # Create the agent with web context and conversation history if available
    agent = create_rag_agent(
        local_context=cleaned_context,
        web_search_enabled=web_search_enabled,
        query=masked_query,
        conversation_history=conversation_context,
    )
    # Generate initial answer
    answer = await generate_answer(prompt=masked_query, agent=agent)
    logger.debug(f"🧠 Answer: {answer}")
    # Apply reflection and potential retries
    final_answer = reflect_and_retry(
        prompt=masked_query, initial_answer=answer, max_retries=2
    )
    logger.debug(f"🧠 Final Answer: {final_answer}")

    # 5.5. Ensure consistent metadata formatting
    # Use the retrieved documents to ensure metadata is properly formatted
    docs_for_metadata = reranked_docs if "reranked_docs" in locals() else []

    # 6. Maske çöz
    final_answer = unmask_text(final_answer)

    # 7. Add assistant response to chat history
    if session_id:
        chat_history_manager.add_message(
            session_id, MessageRole.ASSISTANT, final_answer
        )
    
    
    return {
        "response":final_answer,
        "images": image_datas
    }
