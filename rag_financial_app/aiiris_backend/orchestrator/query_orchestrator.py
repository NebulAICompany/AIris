from typing import List
from retrieval.reranker import rerank
from aiiris_backend.llm.llm_engine import generate_answer
from aiiris_backend.llm.prompt_templates import create_rag_prompt
from aiiris_backend.retrieval.retriever import retrieve_top_k, load_vectorstore

VECTORSTORE_PATH = "aiiris_backend/retrieval/vectorstore"
load_vectorstore(VECTORSTORE_PATH)

def run_orchestration(query: str) -> str:
    retrieved_docs = retrieve_top_k(query=query, k=5)
    
    reranked_docs = rerank(query, retrieved_docs, with_score=False, top_n=3)


    context = "\n\n".join(reranked_docs)
    prompt = create_rag_prompt(context=context, query=query)
    answer = generate_answer(prompt)
    
    return answer
    