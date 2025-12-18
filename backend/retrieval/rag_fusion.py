from typing import List, Dict, Any, Tuple
from backend.core.runner import generate_answer
from backend.core.agents import create_main_agent
from backend.retrieval.retriever import retrieve_top_k
from backend.retrieval.reranker import rerank
from backend.shared.logger import get_logger
from qdrant_client import QdrantClient

logger = get_logger("RAG_FUSION")


async def generate_fusion_queries(
    original_query: str, num_queries: int = 4
) -> List[str]:
    """
    Generate multiple related queries for RAG Fusion using LLM.

    Args:
        original_query: The original user query
        num_queries: Number of additional queries to generate

    Returns:
        List of generated queries including the original
    """
    try:
        # Create a simple agent for query generation
        agent = create_main_agent(
            local_context="",
            web_search_enabled=False,
            instruction="Generate multiple search queries based on the input query",
        )

        generation_prompt = f"""You are a helpful assistant that generates multiple search queries based on a single input query.

Generate {num_queries} different search queries that are related to the original query but approach it from different angles or aspects. These queries should help retrieve comprehensive information about the topic.

Original query: {original_query}

Requirements:
- Generate exactly {num_queries} queries
- Each query should be different but related to the original
- Queries should be in the same language as the original query
- Focus on different aspects, synonyms, or related concepts
- Keep queries concise and searchable

Output format:
1. [Generated query 1]
2. [Generated query 2]
3. [Generated query 3]
4. [Generated query 4]

Generated queries:"""

        response = await generate_answer(generation_prompt, agent)

        # Parse the response to extract queries
        queries = [original_query]  # Always include the original query

        lines = response.strip().split("\n")
        for line in lines:
            line = line.strip()
            if line and (
                line.startswith(("1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.", "9."))
                or line.startswith("-")
            ):
                # Extract query text after the number/bullet
                query_text = (
                    line.split(".", 1)[-1].strip() if "." in line else line[1:].strip()
                )
                if query_text and query_text not in queries:
                    queries.append(query_text)

        # If we didn't get enough queries from parsing, add some basic variations
        if len(queries) < num_queries + 1:
            # Add some simple variations as fallback
            base_variations = [
                f"What is {original_query}?",
                f"Information about {original_query}",
                f"Details on {original_query}",
                f"Explain {original_query}",
            ]

            for variation in base_variations:
                if variation not in queries and len(queries) < num_queries + 1:
                    queries.append(variation)

        logger.info(f"Generated {len(queries)} queries for RAG Fusion: {queries}")
        return queries[: num_queries + 1]  # Limit to requested number + original

    except Exception as e:
        logger.error(f"Error generating fusion queries: {e}")
        # Fallback to original query only
        return [original_query]


def fuse_results(
    search_results_dict: Dict[str, List[Dict[str, Any]]],
    combination_method: str = "rrf",
) -> List[Dict[str, Any]]:
    """
    Fuse multiple results into a single result.
    """
    if combination_method == "rrf":
        return reciprocal_rank_fusion(search_results_dict)
    else:
        return search_results_dict


def reciprocal_rank_fusion(
    search_results_dict: Dict[str, List[Dict[str, Any]]],
) -> List[Dict[str, Any]]:
    """
    Apply Reciprocal Rank Fusion to combine search results from multiple queries.

    Args:
        search_results_dict: Dictionary mapping query -> list of search results

    Returns:
        List of reranked documents with fused scores
    """
    if not search_results_dict:
        return []

    fused_scores = {}
    doc_lookup = {}  # To store document details

    logger.info("Starting Reciprocal Rank Fusion")

    for query, doc_results in search_results_dict.items():
        logger.info(f"Processing query '{query}' with {len(doc_results)} results")

        # Sort results by score (descending) to get proper ranking
        sorted_results = sorted(
            doc_results, key=lambda x: x.get("score", 0), reverse=True
        )

        for rank, doc in enumerate(sorted_results):
            # Create a unique document identifier
            doc_id = _create_doc_id(doc)

            # Store document details for later retrieval
            if doc_id not in doc_lookup:
                doc_lookup[doc_id] = doc

            # Calculate RRF score
            if doc_id not in fused_scores:
                fused_scores[doc_id] = 0

            rrf_score = 1 / (rank + 60)
            fused_scores[doc_id] += rrf_score

            logger.debug(
                f"Doc {doc_id[:50]}... rank {rank} -> RRF score {rrf_score:.4f}, total: {fused_scores[doc_id]:.4f}"
            )

    # Sort by fused scores (descending)
    sorted_doc_ids = sorted(
        fused_scores.keys(), key=lambda x: fused_scores[x], reverse=True
    )

    # Reconstruct documents with fused scores
    reranked_results = []
    for doc_id in sorted_doc_ids:
        doc = doc_lookup[doc_id].copy()
        doc["fusion_score"] = fused_scores[doc_id]
        doc["original_score"] = doc.get("score", 0)  # Preserve original score
        reranked_results.append(doc)

    logger.info(f"RAG Fusion completed: {len(reranked_results)} documents reranked")
    if reranked_results:
        top_scores = [doc["fusion_score"] for doc in reranked_results[:5]]
        logger.info(f"Top 5 fusion scores: {[f'{score:.4f}' for score in top_scores]}")

    return reranked_results


def _create_doc_id(doc: Dict[str, Any]) -> str:
    """
    Create a unique identifier for a document to handle duplicates in RRF.
    """
    metadata = doc.get("metadata", {})

    # Try to create ID from metadata
    chunk_id = metadata.get("chunk_id")
    if chunk_id:
        return chunk_id

    # Fallback to file_name + content hash
    file_name = metadata.get("file_name", "unknown")
    content = doc.get("content", "")
    content_hash = str(hash(content))

    return f"{file_name}_{content_hash}"


async def retrieve_with_fusion(
    client: QdrantClient,
    query: str,
    k: int = 15,
    num_queries: int = 4,
    excessive_k: int = 60,
    final_rerank: bool = True,
    top_n: int = 5,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Retrieve documents using RAG Fusion technique.

    Args:
        query: Original user query
        k: Number of documents to retrieve per query
        num_queries: Number of additional queries to generate
        excessive_k: Fusion parameter
        final_rerank: Whether to apply final reranking with Cohere
        top_n: Final number of documents to return

    Returns:
        Tuple of (final_documents, fusion_metadata)
    """
    try:
        # Step 1: Generate multiple queries
        logger.info(f"🔀 RAG Fusion: Generating queries for '{query}'")
        queries = await generate_fusion_queries(query, num_queries)

        if len(queries) <= 1:
            logger.warning(
                "RAG Fusion: Only original query available, falling back to standard retrieval"
            )
            docs = retrieve_top_k(client, query, k=k)
            return docs[:top_n], {"queries_used": [query], "fusion_applied": False}

        # Step 2: Retrieve documents for each query
        logger.info(f"🔍 RAG Fusion: Retrieving documents for {len(queries)} queries")
        all_results = {}

        for i, fusion_query in enumerate(queries):
            logger.info(f"  Query {i+1}: {fusion_query}")
            search_results = retrieve_top_k(client, fusion_query, k=excessive_k)
            all_results[fusion_query] = search_results
            logger.info(f"    Retrieved {len(search_results)} documents")

        # Step 3: Apply Reciprocal Rank Fusion
        fused_results = fuse_results(all_results, combination_method="rrf")

        if not fused_results:
            logger.warning("RAG Fusion: No results after fusion")
            return [], {
                "queries_used": queries,
                "fusion_applied": True,
                "error": "No results after fusion",
            }

        # Step 4: Optional final reranking
        final_docs = fused_results
        if final_rerank and len(fused_results) > 1:
            try:
                # Prepare documents for reranking (remove fusion scores for reranker)
                rerank_docs = []
                for doc in fused_results:
                    rerank_doc = {
                        "content": doc["content"],
                        "metadata": doc["metadata"],
                    }
                    rerank_docs.append(rerank_doc)

                reranked = rerank(
                    query,
                    rerank_docs,
                    with_score=True,
                    top_n=min(top_n * 2, len(rerank_docs)),
                )

                # Merge rerank scores with fusion scores
                for i, doc in enumerate(reranked):
                    if i < len(fused_results):
                        doc["fusion_score"] = fused_results[i]["fusion_score"]
                        doc["rerank_score"] = doc.get("score", 0)

                final_docs = reranked
                logger.info(
                    f"📊 RAG Fusion: Final reranking completed, {len(final_docs)} documents"
                )

            except Exception as e:
                logger.error(f"Error in final reranking: {e}, using fusion results")
                final_docs = fused_results

        # Step 5: Return top results
        result_docs = final_docs[:top_n]

        fusion_metadata = {
            "queries_used": queries,
            "fusion_applied": True,
            "total_queries": len(queries),
            "documents_per_query": k,
            "final_rerank": final_rerank,
            "total_retrieved": len(fused_results),
            "final_returned": len(result_docs),
        }

        logger.info(
            f"✅ RAG Fusion completed: {len(result_docs)} final documents returned"
        )
        return result_docs, fusion_metadata

    except Exception as e:
        logger.error(f"Error in RAG Fusion: {e}")
        # Fallback to standard retrieval
        docs = retrieve_top_k(client, query, k=k)
        return docs[:top_n], {
            "queries_used": [query],
            "fusion_applied": False,
            "error": str(e),
        }
