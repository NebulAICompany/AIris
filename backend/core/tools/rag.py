from langchain_core.tools import tool
from typing import List, Optional
from backend.retrieval.retriever import (
    get_vectorstore,
    retrieve_with_keyword_helping,
)
from backend.retrieval.reranker import rerank
from backend.shared.logger import get_logger
from backend.shared.constants import get_selected_files

logger = get_logger("RAG_TOOL")


@tool(parse_docstring=True)
def search_local_documents(
    query: str,
    keywords: Optional[List[str]] = None,
    max_results: int = 5,
) -> str:
    """Search uploaded local documents in the knowledge base.

    Use this when you need information from documents that were previously uploaded.

    Args:
        query: Search query to find relevant information in local documents.
        keywords: Optional list of keywords for hybrid vector + keyword search.
        max_results: Maximum number of document chunks to return (default 5, max 10).
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

        # Use global selected_files from shared state
        selected_files = get_selected_files()

        logger.info(
            f"🔍 RAG Tool - Searching with selected files filter: {selected_files}"
        )

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
