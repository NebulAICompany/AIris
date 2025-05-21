from typing import List, Dict, Any
import os
import numpy as np
from langchain_community.vectorstores import FAISS
from langchain_core.embeddings import embeddings
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

_vectorstore = None

def _get_embeddings() -> Embeddings:
    try : 
        from langchain_openai import OpenAIEmbeddings
        return OpenAIEmbeddings(model="text-embedding-3-small", api_key="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")
    except (ImportError,Exception) as e:
        try:
            from langchain_huggingface import HuggingFaceEmbeddings
            return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2", api_key = "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")
        except (ImportError,Exception) as e:
            raise ImportError("No suitable embeddings found. Please install either langchain_openai or langchain_community.") from e


def load_vectorstore(path: str) -> FAISS:
    
    global _vectorstore
    
    if not os.path.exists(path):
        raise FileNotFoundError(f"Vectorstore file not found: {path}")
    
    embeddings = _get_embeddings()
    
    try:
        _vectorstore = FAISS.load_local(folder_path= path,
                                        embeddings= embeddings,
                                        allow_dangerous_deserialization= True)
        print(f"Vectorstore loaded from {path}")
        return _vectorstore
    except Exception as e:
        raise RuntimeError(f"Failed to load vectorstore from {path}: {e}") from e
    
def retrieve_top_k(query: str, k: int = 2) -> List[str]:
    
    global _vectorstore
    
    if _vectorstore is None:
        raise ValueError("Vectorstore not loaded. Please load the vectorstore first.")
    

    try:
        print(f"Retrieving top {k} documents for query: {query}")
        print(_vectorstore)
        docs_with_scores = _vectorstore.similarity_search_with_score(query, k=k)
        print(f"Retrieved {len(docs_with_scores)} documents")   
        return [{
                "content": doc[0].page_content,
                "score": doc[1],
                "metadata": doc[0].metadata,
            } for doc in docs_with_scores]

    except Exception as e:
        print(f"Error during retrieval: {e}")
        return []
