from typing import List
from aiiris_backend.retrieval.reranker import rerank
from aiiris_backend.orchestrator.query_utils import clean_query, spell_check, detect_language, detect_intent
from aiiris_backend.llm.llm_engine import generate_answer
from aiiris_backend.llm.prompt_templates import create_rag_prompt
from aiiris_backend.retrieval.retriever import retrieve_top_k, load_vectorstore

VECTORSTORE_PATH = "aiiris_backend/retrieval/vectorstore"
load_vectorstore(VECTORSTORE_PATH)

def preprocess_query(query: str):
    cleaned = clean_query(query)
    corrected = spell_check(cleaned)
    lang = detect_language(corrected)
    intent, score = detect_intent(corrected)
    
    return corrected, lang, intent

def run_orchestration(query: str) -> str:
    preprocessed_query, lang, intent = preprocess_query(query)
    retrieved_docs = retrieve_top_k(preprocessed_query, k=10)
    
    reranked_docs = rerank(query, retrieved_docs, with_score=False, top_n=3)


    context = "\n\n".join(reranked_docs)
    prompt = create_rag_prompt(context=context, query=query)
    answer = generate_answer(prompt)
    
    return answer
    