from langchain_core.tools import tool
from typing import List, Optional
from backend.retrieval.retriever import (
    get_vectorstore,
    retrieve_with_keyword_helping,
)
from backend.retrieval.reranker import rerank
from backend.shared.logger import get_logger

logger = get_logger("RAG_TOOL")


@tool
def search_local_documents(
    query: str,
    keywords: Optional[List[str]] = None,
    max_results: int = 5,
    selected_files: Optional[List[str]] = None,
) -> str:
    """
    Search through uploaded local documents in the knowledge base.
    Use this tool when you need to find information from documents that were previously uploaded.

    Args:
        query: The search query to find relevant information in local documents.
        keywords: Optional list of keywords/terms for keyword search. If provided, enables hybrid search combining vector and keyword matching.
        max_results: Maximum number of document chunks to return (default: 5, max: 10).
        selected_files: Optional list of specific file names to search within. If not provided, searches all documents.

    Returns:
        A formatted string containing relevant document chunks with their sources.
        Returns "No relevant documents found" if no matches are found.

    Examples:
        - search_local_documents("What is the revenue for Q1?", keywords=["revenue", "Q1"])
        - search_local_documents("financial projections", keywords=["financial", "projections"], max_results=3)
        - search_local_documents("budget analysis", keywords=["budget", "analysis"], selected_files=["budget_2024.pdf"])
    """
    try:
        # Limit max_results to reasonable bounds
        max_results = min(max(1, max_results), 10)

        # Get the global vectorstore client
        client = get_vectorstore()

        # Check if client is available
        if client is None:
            return "Vectorstore is not available. Please ensure documents are uploaded."

        # Check if collection exists
        if not client.collection_exists(collection_name="documents"):
            logger.info("No collection found in vectorstore")
            return "No documents have been uploaded to the knowledge base yet."

        # Use provided keywords or empty list if not provided
        query_terms = keywords if keywords is not None else []

        # Retrieve documents using hybrid search (vector + keyword)
        retrieved_docs = retrieve_with_keyword_helping(
            client=client,
            query=query,
            query_terms=query_terms,
            k=15,
            selected_files=selected_files,
        )

        if not retrieved_docs:
            return "No relevant documents found for your query."

        # Rerank documents
        doc_contents = [
            {"content": doc["content"], "metadata": doc["metadata"]}
            for doc in retrieved_docs
        ]
        reranked_docs = rerank(query, doc_contents, with_score=False, top_n=max_results)

        if not reranked_docs:
            return "No relevant documents found after reranking."

        # Format results
        results = []
        for doc in reranked_docs:
            content = doc["content"]
            metadata = doc.get("metadata", {})
            file_name = metadata.get("file_name", "Unknown")
            page = metadata.get("page", "")

            result_text = f"Source: {file_name}"
            if page:
                result_text += f" (Page {page})"
            result_text += f"\nContent: {content}\n"
            results.append(result_text)

        formatted_results = "\n---\n".join(results)
        return f"Found {len(reranked_docs)} relevant document chunk(s):\n\n{formatted_results}"

    except Exception as e:
        logger.error(f"Error in search_local_documents: {e}")
        return f"Error searching documents: {str(e)}"
