from typing import List, Dict, Any
from qdrant_client import QdrantClient
from langchain_core.embeddings import Embeddings
from backend.shared.constants import OPENAI_API_KEY, HUGGINGFACE_API_KEY
from backend.shared.logger import get_logger

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
        logger.info(
            f"📦 Contains {client.count(collection_name='test_collection')} document chunks (including HyPE prompt expansions)"
        )
        return client
    except Exception as e:
        raise RuntimeError(f"Failed to load vectorstore from {path}: {e}") from e


def retrieve_top_k(client: QdrantClient, query: str, k: int = 10) -> List[Dict[str, Any]]:
    try:
        logger.info(f"🔍 Retrieving top {k} documents for query: {query}")
        logger.info(
            f"📊 Searching through {client.count(collection_name='test_collection')} document chunks (original + HyPE prompt expansions)"
        )
        docs_with_scores = client.query_points(
            collection_name="test_collection",
            query=_get_embeddings().embed_query(query),
            limit=k,
        ).points
        logger.info(
            f"✅ Retrieved {len(docs_with_scores)} documents from vectorstore"
        )

        results = []
        chunks_with_images = 0
        for d in docs_with_scores:
            doc = d.payload
            score = d.score

            content_type = doc["metadata"].get("content_type", "original")

            contains_image = doc["metadata"].get("contains_image", False)
            
            if contains_image:
                chunks_with_images += 1

            # If this is a hypothetical prompt match, we want to return the original content
            # but note that it was found via a prompt match
            if content_type == "hypothetical_prompt":
                # Extract the original content and show the matching prompt
                original_content = doc["metadata"].get(
                    "original_content", doc["page_content"]
                )
                hypothetical_prompt = doc["metadata"].get("hypothetical_prompt", "")

                results.append(
                    {
                        "content": original_content,
                        "score": score,
                        "metadata": {
                            **doc["metadata"],
                            "match_type": "prompt_match",
                            "matching_prompt": hypothetical_prompt,
                            "contains_image": contains_image,
                        },
                    }
                )
            else:
                results.append(
                    {
                        "content": doc["page_content"],
                        "score": score,
                        "metadata": {**doc["metadata"], "match_type": "content_match", "contains_image": contains_image},
                    }
                )
        logger.debug(f"CHUNKS WITH IMAGES IS: {chunks_with_images}")
        # Show breakdown of results
        original_count = sum(
            1 for r in results if r["metadata"].get("content_type") == "original"
        )
        prompt_match_count = sum(
            1 for r in results if r["metadata"].get("match_type") == "prompt_match"
        )
        logger.info(
            f"📈 Results breakdown: {original_count} direct content matches + {prompt_match_count} prompt-based matches"
        )

        return results

    except Exception as e:
        logger.error(f"❌ Error during retrieval: {e}")
        return []
