from typing import List
from aiiris_backend.retrieval.reranker import rerank
from aiiris_backend.orchestrator.query_utils import clean_query, spell_check, detect_language, detect_intent
from aiiris_backend.llm.llm_engine import generate_answer
from aiiris_backend.llm.prompt_templates import create_rag_prompt
from aiiris_backend.retrieval.retriever import retrieve_top_k, load_vectorstore
from aiiris_backend.guardrails.pii_masker import mask_pii, unmask_pii
from aiiris_backend.guardrails.filters import check_input_violations, check_output_violations, sanitize_output

VECTORSTORE_PATH = "aiiris_backend/retrieval/vectorstore"
load_vectorstore(VECTORSTORE_PATH)

def preprocess_query(query: str):
    cleaned = clean_query(query)
    corrected = spell_check(cleaned)
    lang = detect_language(corrected)
    intent, score = detect_intent(corrected)
    
    return corrected, lang, intent

def run_orchestration(query: str) -> str:
    # 1. Temizlik + analiz
    preprocessed_query, lang, intent = preprocess_query(query)

    # 2. Girdi kontrolü (zararlı içerik var mı?)
    input_violations = check_input_violations(preprocessed_query)
    if input_violations:
        return f"Sorgunuz uygunsuz içerikler içeriyor: {input_violations}"

    # 3. Hassas bilgileri maskele
    masked_query, pii_map = mask_pii(preprocessed_query)

    # 4. Retrieval + Reranking
    retrieved_docs = retrieve_top_k(preprocessed_query, k=10)
    
    # Extract only the content from the retrieved docs before reranking
    doc_contents = [doc["content"] for doc in retrieved_docs]
    reranked_docs = rerank(preprocessed_query, doc_contents, with_score=False, top_n=3)


    # 5. Prompt oluştur 
    context = "\n\n".join(reranked_docs)
    prompt = create_rag_prompt(context=context, query=masked_query)

    # 6. Cevabı al
    answer = generate_answer(prompt)

    # 7. Çıktı kontrolü (hallucination, uydurma vs.)
    output_violations = check_output_violations(answer)
    if output_violations:
        answer = sanitize_output(answer, violation_types=None)  # tüm zararlıları sansürle

    # 8. Maske çöz
    final_answer = unmask_pii(answer, pii_map)

    return final_answer
