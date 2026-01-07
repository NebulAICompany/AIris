from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient, models
from langchain_core.embeddings import Embeddings
from backend.shared.constants import OPENAI_API_KEY, HUGGINGFACE_API_KEY
from backend.shared.logger import get_logger
from backend.retrieval.keyword_search import keyword_search

logger = get_logger("RETRIEVER")

_qdrant_client: Optional[QdrantClient] = None

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


def load_vectorstore(path: str) -> QdrantClient:
    global _qdrant_client
    
    if _qdrant_client is not None:
        return _qdrant_client
    
    try:
        _qdrant_client = QdrantClient(path=path)
        logger.info(f"✅ Vectorstore loaded from {path}")
        if _qdrant_client.collection_exists(collection_name="test_collection"):
            logger.info(
                f"📦 Contains {_qdrant_client.count(collection_name='test_collection')} document chunks"
            )
        else:
            logger.info("No collection found")
        return _qdrant_client
    except Exception as e:
        raise RuntimeError(f"Failed to load vectorstore from {path}: {e}") from e


def get_vectorstore() -> Optional[QdrantClient]:
    return _qdrant_client


def close_vectorstore() -> None:
    global _qdrant_client
    if _qdrant_client is not None:
        try:
            _qdrant_client.close()
            logger.info("Qdrant client closed")
        except Exception as e:
            logger.warning(f"Error closing Qdrant client: {e}")
        finally:
            _qdrant_client = None

def retrieve_top_k(
    client: QdrantClient,
    query: str,
    k: int = 10,
    selected_files: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    try:
        logger.info(f"🔍 Retrieving top {k} documents for query: {query}")
        if not client.collection_exists(collection_name="test_collection"):
            logger.info("No collection found")
            return None

        logger.info(
            f"📊 Searching through {client.count(collection_name='test_collection')} document chunks"
        )

        if selected_files:
            selected_files = [file.split(".")[0] for file in selected_files]
            logger.info(f"🔍 Searching through {selected_files} document chunks")
            docs_with_scores = client.query_points(
                collection_name="test_collection",
                query=_get_embeddings().embed_query(query),
                query_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="metadata.file_name",
                            match=models.MatchAny(any=selected_files),
                        )
                    ]
                ),
                limit=k,
                score_threshold=0.3,
            ).points
        else:
            docs_with_scores = client.query_points(
                collection_name="test_collection",
                query=_get_embeddings().embed_query(query),
                limit=k,
                score_threshold=0.3,
            ).points
        logger.info(f"✅ Retrieved {len(docs_with_scores)} documents from vectorstore")

        results = []
        chunks_with_images = 0
        for d in docs_with_scores:
            doc = d.payload
            score = d.score
            logger.info(f"file name: {doc['metadata'].get('file_name')}")
            logger.info(f"score: {score}")
            contains_image = doc["metadata"].get("contains_image", False)

            if contains_image:
                chunks_with_images += 1

            results.append(
                {
                    "content": doc["page_content"],
                    "score": score,
                    "metadata": {
                        **doc["metadata"],
                        "match_type": "content_match",
                        "contains_image": contains_image,
                    },
                }
            )
        logger.info(f"📈 Retrieved {len(results)} document chunks")

        return results

    except Exception as e:
        logger.error(f"❌ Error during retrieval: {e}")
        return []


def retrieve_with_keyword_helping(
    client: QdrantClient,
    query: str,
    query_terms: List[str],
    k: int = 10,
    selected_files: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    try:
        logger.info(f"🔍 Vector + keyword search helping for: '{query}' (limit: {k}+3)")

        # Perform keyword search
        vector_results = retrieve_top_k(
            client, query, k=k, selected_files=selected_files
        )
        results = keyword_search(query_terms, k=3, selected_files=selected_files)
        results = vector_results + results
        logger.info(
            f"✅ Retrieved {len(results)} documents via vector + keyword search helping"
        )

        return results

    except Exception as e:
        logger.error(f"❌ Error during vector + keyword search helping: {e}")
        return []
