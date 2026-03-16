from langchain_core.tools import tool
from typing import List, Optional
from backend.retrieval.retriever import (
    load_vectorstore,
    get_vectorstore,
    retrieve_top_k,
    retrieve_with_keyword_helping,
)
from backend.core.tools.visual import describe_image_content, image_visualizer
from backend.retrieval.reranker import rerank
from backend.shared.logger import get_logger
from backend.shared.constants import (
    VECTORSTORE_PATH_STR,
    get_selected_files,
    get_original_user_query,
)
import asyncio

logger = get_logger("RAG_TOOL")

async def rerank_with_retry(
    query: str,
    doc_contents: List[dict],
    with_score: bool = False,
    top_n: int = 20,
    retries: int = 3,
    delay_seconds: int = 5,
):
    """Retry rerank calls on rate-limit style transient failures."""
    for attempt in range(retries):
        try:
            return rerank(
                query,
                doc_contents,
                with_score=with_score,
                top_n=top_n,
            )
        except Exception as exc:
            is_last_attempt = attempt >= retries - 1
            is_rate_limited = "rate limit" in str(exc).lower()
            if is_rate_limited and not is_last_attempt:
                logger.warning(
                    "Rerank rate limit hit, retrying in %ss... (attempt %s/%s)",
                    delay_seconds,
                    attempt + 1,
                    retries,
                )
                await asyncio.sleep(delay_seconds)
                continue
            raise


@tool(parse_docstring=True, response_format="content_and_artifact")
async def search_local_documents(
    query: str,
    keywords: Optional[List[str]] = None,
) -> str:
    """Search uploaded local documents in the knowledge base.

    Use this when you need information from documents that were previously uploaded.

    Args:
        query: Search query to find relevant information in local documents.
        keywords: Optional list of keywords for hybrid vector + keyword search.
    """
    try:
        client = get_vectorstore()
        if client is None:
            client = await load_vectorstore(VECTORSTORE_PATH_STR)

        if client is None:
            return ("Vectorstore is not available. Please ensure documents are uploaded.", [],)

        if not await client.collection_exists(collection_name="documents"):
            logger.info("No collection found in vectorstore")
            return "No documents have been uploaded to the knowledge base yet.", []

        query_terms = keywords if keywords is not None else []

        selected_files = get_selected_files()
        logger.info(f"🔍 RAG Tool - Searching with selected files filter: {selected_files}")

        retrieved_docs = await retrieve_with_keyword_helping(
            client=client,
            query=query,
            query_terms=query_terms,
            k=15,
            selected_files=selected_files,
        )

        if not retrieved_docs:
            return "No relevant documents found for your query.", []

        doc_contents = [
            {"content": doc["content"], "metadata": doc["metadata"]}
            for doc in retrieved_docs
        ]
        reranked_docs = rerank(query, doc_contents, with_score=False, top_n=5)

        if not reranked_docs:
            return "No relevant documents found after reranking.", []

        results = []
        image_ids = []
        sources = []

        for doc in reranked_docs:
            content = doc["content"]
            metadata = doc.get("metadata", {})
            file_name = metadata.get("file_name", "Unknown")

            result_text = f"{content}\n"
            if metadata.get("contains_image", False):
                image_id = metadata.get("figure_id", "")
                image_ids.append(image_id)
                prompt = f"User Query: {get_original_user_query()}, result text: {result_text}"
                image_description = describe_image_content(image_id, prompt)
                result_text += f"{image_description}\n"

            results.append(result_text)
            sources.append({"name": file_name, "file": file_name})

        formatted_results = "\n---\n".join(results)
        image_visualizer(image_ids)

        content = formatted_results
        artifact = sources

        with open("results.txt", "a") as f:
            f.write(formatted_results)
            f.write("\n")

            
        return content, artifact

    except Exception as e:
        logger.error(f"Error in search_local_documents: {e}")
        return f"Error searching documents: {str(e)}", []


@tool(parse_docstring=True, response_format="content")
async def search_specific_document_for_research(
    query: str,
    file_name: str,
    keywords: Optional[List[str]] = None,
) -> str:
    """Search a specific uploaded document for SPD-RAG research loops.

    Args:
        query: Search query to run against the selected document.
        file_name: Target document name to restrict retrieval to.
        keywords: Optional keyword hints for hybrid retrieval.
    """
    del keywords
    try:
        client = await load_vectorstore(VECTORSTORE_PATH_STR)
        if client is None:
            return "Vectorstore is not available. Please ensure documents are uploaded."

        if not await client.collection_exists(collection_name="documents"):
            logger.info("No collection found in vectorstore")
            return "No documents have been uploaded to the knowledge base yet."

        retrieved_docs = await retrieve_top_k(
            client=client,
            query=query,
            k=15,
            selected_files=[file_name],
        )

        if not retrieved_docs:
            return f"No relevant information found in {file_name} for your query."

        doc_contents = [
            {"content": doc["content"], "metadata": doc["metadata"]}
            for doc in retrieved_docs
        ]
        reranked_docs = await rerank_with_retry(
            query,
            doc_contents,
            with_score=False,
            top_n=5,
        )
        if not reranked_docs:
            return f"No relevant information found in {file_name} after reranking."

        results = []
        for doc in reranked_docs:
            content = doc["content"]
            results.append(f"\n{content}\n")

        return "\n---\n".join(results)
    except Exception as e:
        logger.error(f"Error in search_specific_document_for_research: {e}")
        return f"Error searching specific document: {str(e)}"
