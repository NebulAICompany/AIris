from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient, models
from langchain_core.embeddings import Embeddings
from backend.shared.constants import OPENAI_API_KEY, HUGGINGFACE_API_KEY
from backend.shared.logger import get_logger
from backend.retrieval.keyword_search import keyword_search

logger = get_logger("RETRIEVER")


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
    try:
        client = QdrantClient(path=path)
        logger.info(f"✅ Vectorstore loaded from {path}")
        if client.collection_exists(collection_name="test_collection"):
            logger.info(
                f"📦 Contains {client.count(collection_name='test_collection')} document chunks"
            )
        else:
            logger.info("No collection found")
        return client
    except Exception as e:
        raise RuntimeError(f"Failed to load vectorstore from {path}: {e}") from e


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
            f"📊 Searching through {client.count(collection_name='test_collection')} document chunks (original + HyPE prompt expansions)"
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
            ).points
        else:
            docs_with_scores = client.query_points(
                collection_name="test_collection",
                query=_get_embeddings().embed_query(query),
                limit=k,
            ).points
        logger.info(f"✅ Retrieved {len(docs_with_scores)} documents from vectorstore")

        results = []
        chunks_with_images = 0
        for d in docs_with_scores:
            doc = d.payload
            score = d.score
            logger.info(f"file name: {doc['metadata'].get('file_name')}")
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
        logger.debug("CHUNKS WITH IMAGES IS: ", chunks_with_images)
        logger.info(f"📈 Retrieved {len(results)} document chunks")

        return results

    except Exception as e:
        logger.error(f"❌ Error during retrieval: {e}")
        return []


def retrieve_with_keyword_search(
    query_terms: List[str], k: int = 10, selected_files: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    try:
        logger.info(f"🔍 Keyword search for terms: {query_terms} (limit: {k})")

        # Perform keyword search
        results = keyword_search(query_terms, k=k, selected_files=selected_files)

        logger.info(f"✅ Retrieved {len(results)} documents via keyword search")
        return results

    except Exception as e:
        logger.error(f"❌ Error during keyword search: {e}")
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


def retrieve_hybrid(
    client: QdrantClient,
    query: str,
    query_terms: List[str],
    k: int = 10,
    selected_files: Optional[List[str]] = None,
    vector_weight: float = 0.5,
    keyword_weight: float = 0.5,
) -> List[Dict[str, Any]]:
    """
    Retrieve documents using hybrid search (vector + keyword)

    Args:
        client: Qdrant client for vector search
        query: Search query
        query_terms: Pre-processed search terms for keyword search
        k: Number of documents to retrieve
        selected_files: Optional list of files to search in
        vector_weight: Weight for vector search scores
        keyword_weight: Weight for keyword search scores

    Returns:
        List of retrieved documents with combined scores
    """
    try:
        logger.info(f"🔍 Hybrid search for: '{query}' (limit: {k})")

        # Get results from both methods
        vector_results = retrieve_top_k(
            client, query, k=k * 2, selected_files=selected_files
        )
        keyword_results = retrieve_with_keyword_search(
            query_terms, k=k * 2, selected_files=selected_files
        )

        # Normalize scores and combine results
        combined_results = {}

        # Add vector results with normalized scores
        if vector_results:
            max_vector_score = max(result["score"] for result in vector_results)
            for result in vector_results:
                doc_key = result["metadata"].get("chunk_id", "")
                normalized_score = (
                    result["score"] / max_vector_score if max_vector_score > 0 else 0
                )
                combined_results[doc_key] = {
                    **result,
                    "score": normalized_score * vector_weight,
                    "vector_score": result["score"],
                    "keyword_score": 0.0,
                    "search_method": "hybrid",
                }

        # Add keyword results with normalized scores
        if keyword_results:
            max_keyword_score = max(result["score"] for result in keyword_results)
            for result in keyword_results:
                doc_key = result["metadata"].get("chunk_id", "")
                normalized_score = (
                    result["score"] / max_keyword_score if max_keyword_score > 0 else 0
                )

                if doc_key in combined_results:
                    # Document found in both - combine scores
                    combined_results[doc_key]["score"] += (
                        normalized_score * keyword_weight
                    )
                    combined_results[doc_key]["keyword_score"] = result["score"]
                    if "matched_terms" in result["metadata"]:
                        combined_results[doc_key]["metadata"]["matched_terms"] = result[
                            "metadata"
                        ]["matched_terms"]
                else:
                    # Document only in keyword results
                    combined_results[doc_key] = {
                        **result,
                        "score": normalized_score * keyword_weight,
                        "vector_score": 0.0,
                        "keyword_score": result["score"],
                        "search_method": "hybrid",
                    }

        # Sort by combined score and return top k
        final_results = sorted(
            combined_results.values(), key=lambda x: x["score"], reverse=True
        )[:k]

        logger.info(
            f"✅ Hybrid search: {len(vector_results)} vector + {len(keyword_results)} keyword → {len(final_results)} final results"
        )
        return final_results

    except Exception as e:
        logger.error(f"❌ Error during hybrid search: {e}")
        # Fallback to vector search only
        return retrieve_top_k(client, query, k=k, selected_files=selected_files)
