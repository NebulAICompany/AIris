from typing import List, Optional, Dict, Tuple
from backend.retrieval.reranker import rerank
from backend.orchestrator.query_utils import (
    spell_check,
    detect_language,
)
from backend.core.runner import generate_answer
from backend.core.agents import create_rag_agent
from backend.retrieval.retriever import retrieve_top_k, load_vectorstore
from backend.guardrails.pii import mask_text, unmask_text
from backend.guardrails.filters import check_openai_moderation
from .reflection import reflect_and_retry
from backend.core.chat import chat_history_manager, MessageRole
import os
import re
import base64

VECTORSTORE_PATH = "backend/vectorstore"


def filter_docs_by_selected_files(
    docs: List, selected_files: Optional[List[str]]
) -> List:
    """
    Filter retrieved documents to only include those from selected files.
    If selected_files is None or empty, return all documents.
    """
    if not selected_files or len(selected_files) == 0:
        return docs

    filtered_docs = []
    for doc in docs:
        metadata = doc.get("metadata", {})
        file_name = metadata.get("file_name", "")

        # Check if this document's file is in the selected files list
        if file_name in selected_files:
            filtered_docs.append(doc)

    print(
        f"   - Filtered {len(docs)} docs to {len(filtered_docs)} based on selected files"
    )
    return filtered_docs


def preprocess_query(query: str):
    lang = detect_language(query)
    print(f"Detected Language: {lang}")
    if lang=="Turkish":
        corrected = spell_check(query)
        return corrected, lang
    return query, lang

def extract_image_references_from_context(local_context: str) -> Tuple[str, List[str]]:
    """
    Analyze local context for image references and extract image paths.
    Returns (cleaned_context, image_paths_list)
    """
    image_pattern = r'\(\(Image\):([^)]+)\)'
    image_paths = []
    
    print(f"🔍 Analyzing local context for image references...")
    
    # Find all image references in the context
    matches = re.findall(image_pattern, local_context)
    
    if matches:
        print(f"   - Found {len(matches)} image references in context")
        for match in matches:
            image_path = match.strip()
            if image_path not in image_paths:
                image_paths.append(image_path)
    
        # Clean the context from image references
    cleaned_context = re.sub(image_pattern, '', local_context)

    return cleaned_context, image_paths

def load_images_from_paths(image_paths: List[str]) -> List[Dict]:
    """
    Load actual image files based on the extracted paths and convert to base64.
    Returns list of image data dictionaries.
    """
    images_data = []
    
    if not image_paths:
        return images_data
    
    print(f"📁 Loading {len(image_paths)} images from filesystem...")
    
    for path in image_paths:
        # Construct the full image path - try both .jpg and .png
        for ext in ['.jpg', '.png']:
            image_file_path = f"backend/images/{path}{ext}"
            
            if os.path.exists(image_file_path):
                try:
                    with open(image_file_path, "rb") as img_file:
                        img_data = base64.b64encode(img_file.read()).decode('utf-8')
                        images_data.append({
                            "filename": f"{path}{ext}",
                            "data": img_data,
                            "reference": path,
                            "type": f"image/{ext[1:]}"  # jpeg or png
                        })
                    break  # Found the file, no need to try other extensions
                except Exception as e:
                    print(f"   ❌ Error loading image {path}{ext}: {e}")

    
    return images_data

async def run_orchestration(
    query: str,
    web_search_enabled: bool,
    wolfram_enabled: bool = False,
    pre_embedding_process: str = "none",
    session_id: Optional[str] = None,
    selected_files: Optional[List[str]] = None,
) -> str:
    print(f"🔍 Query Orchestrator started:")
    print(f"   - Query: {query}")
    print(f"   - Web Search Enabled: {web_search_enabled}")
    print(f"   - Wolfram Enabled: {wolfram_enabled}")
    print(f"   - Pre-embedding Process: {pre_embedding_process}")
    print(f"   - Session ID: {session_id}")
    print(f"   - Selected Files: {selected_files}")

    # Handle chat history and session management
    if session_id:
        # Add user message to chat history
        chat_history_manager.add_message(session_id, MessageRole.USER, query)

        # Get conversation context
        conversation_context = chat_history_manager.get_conversation_context(
            session_id, max_messages=10
        )
        print(f"   - Conversation context: {len(conversation_context)} messages")

        # Reduce history if too long
        session = chat_history_manager.get_session(session_id)
        if session and len(session.messages) > 30:
            print(f"   - Reducing chat history from {len(session.messages)} messages")
            chat_history_manager.reduce_history(session, target_messages=20)
    else:
        conversation_context = []
        print(f"   - No session ID provided, processing as standalone query")

    # Vectorstore'ı yükle
    if os.path.exists(f"{VECTORSTORE_PATH}/index.faiss"):
        print(f"Loading vectorstore from {VECTORSTORE_PATH}")
        if pre_embedding_process == "cch":
            print(
                "   - Contextual Chunk Headers (CCH) enhanced chunks will be used for retrieval"
            )
        elif pre_embedding_process == "hype":
            print(
                "   - HyPE (Hypothetical Prompt Embeddings) enhanced chunks will be used for retrieval"
            )
        else:
            print("   - Standard chunks will be used for retrieval")
        load_vectorstore(VECTORSTORE_PATH)

    # 1. Temizlik + analiz
    preprocessed_query, lang = preprocess_query(query)

    # 2. Girdi kontrolü (OpenAI moderation)
    input_moderation = check_openai_moderation(preprocessed_query)
    if input_moderation["flagged"]:
        return f"Sorgunuz uygunsuz içerikler içeriyor: {input_moderation['violations']}"

    # 3. Hassas bilgileri maskele
    masked_query = mask_text(preprocessed_query)
    print(f"Masked Query: {masked_query}")

    ENABLED_RAG_TECHNIQUES = ["rse"]

    if "rag_fusion" in ENABLED_RAG_TECHNIQUES:
        # 4. Enhanced Retrieval with RAG Fusion (Multiple Query Generation + RRF)
        from backend.retrieval.rag_fusion import retrieve_with_fusion

        fusion_docs, fusion_metadata = await retrieve_with_fusion(
            preprocessed_query, k=15, num_queries=4, top_n=5, final_rerank=True, excessive_k=60
        )

        if not fusion_docs:
            return "Üzgünüm, sorgunuzla ilgili belgede bilgi bulamadım."

        print(f"🔀 RAG Fusion Results: {fusion_metadata}")

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
        # print(f"RSE Chunks: {rse_chunks[0]}\n RSE Scores: {rse_scores[0]}")

        # Filter RSE chunks by selected files
        filtered_rse_chunks = filter_docs_by_selected_files(rse_chunks, selected_files)

        if not filtered_rse_chunks:
            if selected_files:
                return f"Üzgünüm, seçilen dosyalarda ({', '.join(selected_files)}) sorgunuzla ilgili bilgi bulamadım."
            else:
                return "Üzgünüm, sorgunuzla ilgili belgede bilgi bulamadım."

        # Use filtered RSE-enhanced chunks directly (they're already optimized)
        reranked_docs = filtered_rse_chunks[:5]  # Take top 5 RSE segments
    else:
        # 4. Enhanced Retrieval + Reranking (HyPE benefits are built into the vectorstore)
        retrieved_docs = retrieve_top_k(
            preprocessed_query, k=15
        )  # Get more docs for better reranking

        if not retrieved_docs:
            return "Üzgünüm, sorgunızla ilgili belgede bilgi bulamadım."

        # Filter retrieved docs by selected files
        filtered_retrieved_docs = filter_docs_by_selected_files(
            retrieved_docs, selected_files
        )

        if not filtered_retrieved_docs:
            if selected_files:
                return f"Üzgünüm, seçilen dosyalarda ({', '.join(selected_files)}) sorgunuzla ilgili bilgi bulamadım."
            else:
                return "Üzgünüm, sorgunuzla ilgili belgede bilgi bulamadım."

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
    print(f"   - Local Context: {local_context}")
    print("using web search ?= ", web_search_enabled)

    cleaned_context, image_paths = extract_image_references_from_context(local_context)

    image_datas = load_images_from_paths(image_paths)

    # Create the agent with web context and conversation history if available
    agent = create_rag_agent(
        local_context=cleaned_context,
        web_search_enabled=web_search_enabled,
        query=masked_query,
        wolfram_enabled=wolfram_enabled,
        conversation_history=conversation_context,
    )
    # Generate initial answer
    answer = await generate_answer(prompt=masked_query, agent=agent)
    print(f"🧠 Answer: {answer}")
    # Apply reflection and potential retries
    final_answer = await reflect_and_retry(
        prompt=masked_query, initial_answer=answer, agent=agent, max_retries=2
    )
    print(f"🧠 Final Answer: {final_answer}")

    # 5.5. Ensure consistent metadata formatting
    # Use the retrieved documents to ensure metadata is properly formatted
    docs_for_metadata = reranked_docs if "reranked_docs" in locals() else []


    # 6. Çıktı kontrolü (OpenAI moderation)
    output_moderation = check_openai_moderation(final_answer)
    if output_moderation["flagged"]:
        # OpenAI moderation flagged content - return a safe response
        final_answer = "Üzgünüm, bu yanıt uygun değil. Lütfen farklı bir soru sorun."

    # 7. Maske çöz
    final_answer = unmask_text(final_answer)

    # 8. Add assistant response to chat history
    if session_id:
        chat_history_manager.add_message(
            session_id, MessageRole.ASSISTANT, final_answer
        )
    
    
    return {
        "response":final_answer,
        "images": image_datas
    }
