from typing import List
from aiiris_backend.retrieval.reranker import rerank
from aiiris_backend.orchestrator.query_utils import (
    clean_query,
    spell_check,
    detect_language,
    detect_intent,
)
from aiiris_backend.llm.llm_engine import generate_answer
from aiiris_backend.llm.prompt_templates import create_rag_agent
from aiiris_backend.retrieval.retriever import retrieve_top_k, load_vectorstore
from aiiris_backend.guardrails.pii_masker import mask_pii
from aiiris_backend.guardrails.pii_deneme import pii_unmask
from aiiris_backend.guardrails.filters import (
    check_input_violations,
    check_output_violations,
    sanitize_output,
)
from .reflection import reflect_and_retry
import os

VECTORSTORE_PATH = "aiiris_backend/vectorstore"
FILES_PATH = "aiiris_backend/files"


def preprocess_query(query: str):
    cleaned = clean_query(query)
    print(f"Cleaned Query: {cleaned}")
    corrected = spell_check(cleaned)
    print(f"Corrected Query: {corrected}")
    lang = detect_language(corrected)
    print(f"Detected Language: {lang}")
    intent, score = detect_intent(corrected)

    return corrected, lang, intent


async def run_orchestration(
    query: str, web_search_enabled: bool, wolfram_enabled: bool = False
) -> str:
    print(f"🔍 Query Orchestrator started:")
    print(f"   - Query: {query}")
    print(f"   - Web Search Enabled: {web_search_enabled}")
    print(f"   - Wolfram Enabled: {wolfram_enabled}")

    # Vectorstore'ı yükle
    if os.path.exists(f"{VECTORSTORE_PATH}/index.faiss"):
        print(f"Loading vectorstore from {VECTORSTORE_PATH}")
        load_vectorstore(VECTORSTORE_PATH)

    # 1. Temizlik + analiz
    preprocessed_query, lang, intent = preprocess_query(query)

    # 2. Girdi kontrolü (zararlı içerik var mı?)
    input_violations = check_input_violations(preprocessed_query)
    if input_violations:
        return f"Sorgunuz uygunsuz içerikler içeriyor: {input_violations}"

    # 3. Hassas bilgileri maskele
    masked_query, pii_map = mask_pii(preprocessed_query)
    print(f"Masked Query: {masked_query}")

    # 4. Enhanced Retrieval + Reranking (HyPE benefits are built into the vectorstore)
    retrieved_docs = retrieve_top_k(
        preprocessed_query, k=15
    )  # Get more docs for better reranking
    print(type(retrieved_docs))

    if not retrieved_docs:
        return "Üzgünüm, sorgunuzla ilgili belgede bilgi bulamadım."

    # Extract only the content from the retrieved docs before reranking
    doc_contents = [
        {"content": doc["content"], "metadata": doc["metadata"]}
        for doc in retrieved_docs
    ]

    reranked_docs = rerank(preprocessed_query, doc_contents, with_score=False, top_n=5)

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

    print("using web search ?= ", web_search_enabled)

    # Create the agent with web context if available
    agent = create_rag_agent(
        local_context=local_context,
        web_search_enabled=web_search_enabled,
        query=masked_query,
        mcp_servers=[],
        wolfram_enabled=wolfram_enabled,
    )

    # Generate initial answer
    answer = await generate_answer(prompt=masked_query, agent=agent)

    # Apply reflection and potential retries
    final_answer = await reflect_and_retry(
        prompt=masked_query, initial_answer=answer, agent=agent, max_retries=2
    )

    # 6. Çıktı kontrolü (hallucination, uydurma vs.)
    output_violations = check_output_violations(final_answer)
    if output_violations:
        final_answer = sanitize_output(
            final_answer, violation_types=None
        )  # tüm zararlıları sansürle

    # 7. Maske çöz
    final_answer = pii_unmask(final_answer, pii_map)

    return final_answer
