from typing import List, Optional, Dict, Any
from backend.retrieval.reranker import rerank
from backend.core.runner import generate_answer
from backend.core.agents import create_rag_agent
from backend.retrieval.retriever import (
    retrieve_top_k,
    retrieve_with_keyword_search,
    retrieve_hybrid,
    load_vectorstore,
    retrieve_with_keyword_helping,
)
from backend.security.pii import mask_text, unmask_text
from backend.security.filters import check_openai_moderation
from backend.utils.query import (
    spell_check,
    detect_language,
    filter_docs_by_selected_files,
    refine_query,
)
from backend.core.chat import chat_history_manager, MessageRole
from backend.shared.constants import VECTORSTORE_PATH_STR
from backend.core.tools.visual import get_image_datas, clear_image_datas
from backend.shared.logger import get_logger
from backend.server.finance_mcp import get_chart_datas, clear_chart_datas
from backend.core.tools.office import get_generated_files, clear_generated_files

logger = get_logger("QUERY_PIPELINE")


def preprocess_query(query: str):
    lang = detect_language(query)
    logger.debug(f"Detected Language: {lang}")
    # if lang=="Turkish":
    #     corrected = spell_check(query)
    #     return corrected, lang
    return query, lang


async def run_orchestration(
    query: str,
    web_search_enabled: bool,
    pre_embedding_process: str = "none",
    session_id: Optional[str] = None,
    selected_files: Optional[List[str]] = None,
    search_method: str = "vector",  # "vector", "keyword", or "hybrid"
) -> Dict[str, Any]:

    logger.info(f"🔍 Query Orchestrator started:")
    logger.info(f"   - Query: {query}")
    logger.info(f"   - Web Search Enabled: {web_search_enabled}")
    logger.info(f"   - Pre-embedding Process: {pre_embedding_process}")
    logger.info(f"   - Search Method: {search_method}")
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
            logger.info(
                f"   - Reducing chat history from {len(session.messages)} messages"
            )
            chat_history_manager.reduce_history(session, target_messages=20)
    else:
        conversation_context = []
        logger.debug(f"   - No session ID provided, processing as standalone query")

    client = load_vectorstore(VECTORSTORE_PATH_STR)

    # 1. Temizlik + analiz
    preprocessed_query, lang = preprocess_query(query)
    logger.info(f"   - Preprocessed Query before refinement: {preprocessed_query}")

    preprocessed_query = refine_query(preprocessed_query, lang)
    logger.info(f"   - Query after refinement: {preprocessed_query}")

    # 2. Girdi kontrolü (OpenAI moderation)
    input_moderation = check_openai_moderation(preprocessed_query)
    if input_moderation["flagged"]:
        logger.warning("moderation error")
        return {
            "response": f"Sorgunuz uygunsuz içerikler içeriyor: {input_moderation['violations']}",
            "images": [],
            "charts": [],
        }

    # 3. Hassas bilgileri maskele
    masked_query_list = await mask_text([preprocessed_query], "query")
    masked_query = masked_query_list[0]
    logger.debug(f"Masked Query: {masked_query}")

    ENABLED_RAG_TECHNIQUES = []

    if "rag_fusion" in ENABLED_RAG_TECHNIQUES:
        # 4. Enhanced Retrieval with RAG Fusion (Multiple Query Generation + RRF)
        from backend.retrieval.rag_fusion import retrieve_with_fusion

        fusion_docs, fusion_metadata = await retrieve_with_fusion(
            client=client,
            query=preprocessed_query,
            k=15,
            num_queries=4,
            top_n=5,
            final_rerank=True,
            excessive_k=60,
        )

        if not fusion_docs:
            return {
                "response": "Üzgünüm, sorgunuzla ilgili belgede bilgi bulamadım.",
                "images": [],
                "charts": [],
            }

        logger.debug(f"🔀 RAG Fusion Results: {fusion_metadata}")

        # Filter fusion docs by selected files
        filtered_fusion_docs = filter_docs_by_selected_files(
            fusion_docs, selected_files
        )

        if not filtered_fusion_docs:
            if selected_files:
                return {
                    "response": f"Üzgünüm, seçilen dosyalarda ({', '.join(selected_files)}) sorgunuzla ilgili bilgi bulamadım.",
                    "images": [],
                    "charts": [],
                }
            else:
                return {
                    "response": "Üzgünüm, sorgunuzla ilgili belgede bilgi bulamadım.",
                    "images": [],
                    "charts": [],
                }

        # Use filtered fusion docs directly (they're already optimized and reranked)
        reranked_docs = filtered_fusion_docs
    elif "rse" in ENABLED_RAG_TECHNIQUES:
        # 4. Enhanced Retrieval with RSE (Relevant Segment Extraction)
        from backend.retrieval.rse import retrieve_with_rse

        rse_chunks, rse_scores = retrieve_with_rse(
            client=client, query=preprocessed_query, k=15
        )

        if not rse_chunks:
            return {
                "response": "Üzgünüm, sorgunuzla ilgili belgede bilgi bulamadım.",
                "images": [],
                "charts": [],
            }
        # logger.debug(f"RSE Chunks: {rse_chunks[0]}\n RSE Scores: {rse_scores[0]}")

        # Filter RSE chunks by selected files
        filtered_rse_chunks = filter_docs_by_selected_files(rse_chunks, selected_files)

        if not filtered_rse_chunks:
            if selected_files:
                return {
                    "response": f"Üzgünüm, seçilen dosyalarda ({', '.join(selected_files)}) sorgunuzla ilgili bilgi bulamadı.",
                    "images": [],
                    "charts": [],
                }
            else:
                return {
                    "response": "Üzgünüm, sorgunuzla ilgili belgede bilgi bulamadım.",
                    "images": [],
                    "charts": [],
                }

        # Use filtered RSE-enhanced chunks directly (they're already optimized)
        reranked_docs = filtered_rse_chunks[:5]  # Take top 5 RSE segments
    else:
        # 4. Enhanced Retrieval + Reranking
        if search_method == "keyword":
            logger.info("🔍 Using keyword search (BM25)")
            retrieved_docs = retrieve_with_keyword_search(
                query=preprocessed_query, k=15, selected_files=selected_files
            )
        elif search_method == "hybrid":
            logger.info("🔍 Using hybrid search (vector + keyword)")
            retrieved_docs = retrieve_hybrid(
                client=client,
                query=preprocessed_query,
                k=15,
                selected_files=selected_files,
            )
        elif search_method == "vector_keyword_helping":
            logger.info("🔍 Using vector + keyword search helping")
            retrieved_docs = retrieve_with_keyword_helping(
                client=client,
                query=preprocessed_query,
                k=15,
                selected_files=selected_files,
            )
        else:  # Default to vector search
            logger.info("🔍 Using vector search")
            retrieved_docs = retrieve_top_k(
                client=client,
                query=preprocessed_query,
                k=15,
                selected_files=selected_files,
            )  # Get more docs for better reranking

        if not retrieved_docs:
            logger.warning("No retrieved docs")
            return {
                "response": "Üzgünüm, sorgunızla ilgili belgede bilgi bulamadı.",
                "images": [],
                "charts": [],
            }

        # Extract only the content from the retrieved docs before reranking
        doc_contents = [
            {"content": doc["content"], "metadata": doc["metadata"]}
            for doc in retrieved_docs
        ]
        reranked_docs = rerank(
            preprocessed_query, doc_contents, with_score=False, top_n=5
        )

    context_entries = []

    included_parent_chunk_ids = []
    for doc in reranked_docs:
        if (
            pre_embedding_process == "pdr"
            and doc["metadata"].get("content_type") == "child"
        ):
            if doc["metadata"].get("parent_chunk_id") in included_parent_chunk_ids:
                continue
            else:
                content = doc["metadata"].get("parent_content")
                included_parent_chunk_ids.append(doc["metadata"].get("parent_chunk_id"))

        else:
            included_parent_chunk_ids.append(doc["metadata"].get("chunk_id"))
            content = doc["content"]

        metadata = doc["metadata"]

        metadata_str = ""
        metadata_str += f"Source: {metadata.get('file_name')}\n"
        if (
            pre_embedding_process == "pdr"
            and doc["metadata"].get("content_type") == "child"
        ):
            metadata_str += f"Parent Chunk ID: {metadata.get('parent_chunk_id')}\n"
        context_entries.append(
            f"Lokal İçerik: {content}\n\n Lokal Metadata:\n{metadata_str}"
        )

    local_context = "\n\n---\n\n".join(context_entries)
    logger.info(f"In Query, Pre-embedding process: {pre_embedding_process}")
    logger.debug(f"   - Local Context: {local_context}")
    logger.info(f"using web search ?= {web_search_enabled}")

    agent = create_rag_agent(
        local_context=local_context,
        web_search_enabled=web_search_enabled,
        query=masked_query,
        conversation_history=conversation_context,
    )
    # Generate initial answer
    answer = await generate_answer(prompt=masked_query, agent=agent)
    logger.debug(f"🧠 Answer: {answer}")
    # 5.5. Ensure consistent metadata formatting
    # Use the retrieved documents to ensure metadata is properly formatted
    docs_for_metadata = reranked_docs if "reranked_docs" in locals() else []

    # 6. Maske çöz
    final_answer = unmask_text(answer)

    # 7. Get images, charts, and generated files and add assistant response to chat history
    images = get_image_datas()
    charts = get_chart_datas()
    generated_files = get_generated_files()

    if session_id:
        metadata = {}
        if images:
            metadata["images"] = images
        if charts:
            metadata["charts"] = charts
        if generated_files:
            metadata["generatedFiles"] = generated_files

        metadata = metadata if metadata else None
        chat_history_manager.add_message(
            session_id, MessageRole.ASSISTANT, final_answer, metadata
        )

    clear_generated_files()
    clear_image_datas()
    clear_chart_datas()

    return {
        "response": final_answer,
        "images": images,
        "charts": charts,
        "generatedFiles": generated_files,
    }
