from typing import List, Dict, Any
import os
from langchain_community.vectorstores import FAISS
from langchain_core.embeddings import Embeddings
from backend.shared.constants import OPENAI_API_KEY, HUGGINGFACE_API_KEY
from backend.shared.logger import get_logger

logger = get_logger("RETRIEVER")
_vectorstore = None

def _get_embeddings() -> Embeddings:
    try:
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(
            model="text-embedding-3-small",
            api_key=OPENAI_API_KEY,
        )
    except (ImportError, Exception) as e:
        try:
            from langchain_huggingface import HuggingFaceEmbeddings

            return HuggingFaceEmbeddings(
                model_name="sentence-transformers/all-MiniLM-L6-v2",
                api_key=HUGGINGFACE_API_KEY,
            )
        except (ImportError, Exception) as e:
            raise ImportError(
                "No suitable embeddings found. Please install either langchain_openai or langchain_community."
            ) from e

def load_vectorstore(path: str) -> FAISS:
    global _vectorstore

    if not os.path.exists(path):
        raise FileNotFoundError(f"Vectorstore file not found: {path}")

    embeddings = _get_embeddings()

    try:
        _vectorstore = FAISS.load_local(
            folder_path=path,
            embeddings=embeddings,
            allow_dangerous_deserialization=True,
        )
        logger.info(f"✅ Vectorstore loaded from {path}")
        logger.info(
            f"📦 Contains {_vectorstore.index.ntotal} document chunks"
        )
        return _vectorstore
    except Exception as e:
        raise RuntimeError(f"Failed to load vectorstore from {path}: {e}") from e


def retrieve_top_k(query: str, k: int = 10) -> List[Dict[str, Any]]:
    global _vectorstore

    if _vectorstore is None:
        raise ValueError("Vectorstore not loaded. Please load the vectorstore first.")

    try:
        logger.info(f"🔍 Retrieving top {k} documents for query: {query}")
        logger.info(
            f"📊 Searching through {_vectorstore.index.ntotal} document chunks "
        )
        docs_with_scores = _vectorstore.similarity_search_with_score(query, k=k)
        logger.info(
            f"✅ Retrieved {len(docs_with_scores)} documents from vectorstore"
        )

        results = []
        chunks_with_images = 0
        for doc, score in docs_with_scores:
            contains_image = doc.metadata.get("contains_image", False)
            
            if contains_image:
                chunks_with_images += 1

            results.append(
                {
                    "content": doc.page_content,
                    "score": score,
                    "metadata": {**doc.metadata, "match_type": "content_match", "contains_image": contains_image},
                }
            )
        logger.debug("CHUNKS WITH IMAGES IS: ", chunks_with_images)
        logger.info(f"📈 Retrieved {len(results)} document chunks")

        return results

    except Exception as e:
        logger.error(f"❌ Error during retrieval: {e}")
        return []