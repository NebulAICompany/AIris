from typing import List
from backend.shared.logger import get_logger
from backend.shared.constants import OPENAI_MODEL
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage
import re

logger = get_logger("AUTOCONTEXT")


class AutoContextProcessor:
    """
    AutoContext processor that creates contextual chunk headers for improved RAG retrieval.

    Based on the dsRAG approach, this module generates document-level and section-level
    context headers that are prepended to chunks before embedding. This dramatically
    improves retrieval quality by providing more complete context representation.
    """

    def __init__(
        self,
        use_document_summary: bool = True,
    ):
        """
        Initialize the AutoContext processor.

        Args:
            use_document_summary: Whether to generate document-level summaries
        """
        self.use_document_summary = use_document_summary

    async def generate_document_title(
        self, document_text: str, existing_title: str = None
    ) -> str:
        """
        Generate a descriptive title for the document if none exists.

        Args:
            document_text: Full text of the document
            existing_title: Existing title if available

        Returns:
            Generated or existing document title
        """
        if existing_title and existing_title.strip():
            return existing_title.strip()

        try:
            title_prompt = f"""You are a document analyst. Create a short and descriptive title for the document below.

Document content (first 2000 characters):
{document_text[:2000]}

Requirements:
- The title must be less than 100 characters
- It should be descriptive and specific
- Focus on the main topic or purpose
- Use professional language
- Do not use quotes or special formatting
- Write the title in the language of the document. THIS IS VERY IMPORTANT.

Generated title:"""

            # Use standard API call instead of agent
            response = await OPENAI_MODEL.ainvoke([HumanMessage(content=title_prompt)])
            title = response.content.strip()

            # Clean up the response
            # Remove quotes if present
            title = re.sub(r'^["\']|["\']$', "", title)
            # Limit length
            if len(title) > 100:
                title = title[:97] + "..."

            return title

        except Exception as e:
            logger.error(f"Error generating document title: {e}")
            return "Document"

    async def generate_document_summary(
        self, document_text: str, document_title: str
    ) -> str:
        """
        Generate a summary of the entire document.
        Args:
            document_text: Full text of the document
            document_title: Title of the document

        Returns:
            Document summary
        """
        if not self.use_document_summary:
            return ""

        try:
            summary_prompt = f"""You are a document analyst. Generate a comprehensive summary of the document below.

Document Title: {document_title}

Document content (first 4000 characters):
{document_text[:4000]}

Requirements:
- Provide a 2-3 sentence summary
- Focus on the main topics, purpose, and key information
- Be concise but informative
- Use professional language
- Do not use quotes or special formatting
- Write the summary in the language of the document. THIS IS VERY IMPORTANT.

Document summary:"""

            # Use standard API call instead of agent
            response = await OPENAI_MODEL.ainvoke(
                [HumanMessage(content=summary_prompt)]
            )
            summary = response.content.strip()

            # Clean up the response
            # Remove any quotes
            summary = re.sub(r'^["\']|["\']$', "", summary)
            return summary

        except Exception as e:
            logger.error(f"Error generating document summary: {e}")
            return f"This document titled '{document_title}' contains important information."

    def create_contextual_header(
        self,
        chunk_text: str,
        file_name: str = None,
        document_title: str = None,
        document_summary: str = None,
    ) -> str:
        """
        Create a contextual header for a chunk.

        Args:
            chunk_text: Original chunk text
            file_name: File name
            document_title: Document title
            document_summary: Document summary

        Returns:
            Chunk with contextual header prepended
        """
        header_parts = []

        # Document context
        if file_name:
            header_parts.append(f"File: {file_name}")

        if document_title:
            header_parts.append(f"Document: {document_title}")

        if document_summary:
            header_parts.append(f"Document Summary: {document_summary}")

        # Create the contextual header
        if header_parts:
            contextual_header = "Context: " + " | ".join(header_parts)
            return f"{contextual_header}\n\nContent: {chunk_text}"
        else:
            return chunk_text

    async def process_document_chunks(
        self, chunks: List[Document], document_title: str = None, file_name: str = None
    ) -> List[Document]:
        """
        Process document chunks to add contextual headers.

        Args:
            chunks: List of document chunks
            document_title: Optional document title
            file_name: Optional file name for context

        Returns:
            List of chunks with contextual headers
        """
        if not chunks:
            return chunks

        # Reconstruct document text from chunks
        document_text = "\n\n".join([chunk.page_content for chunk in chunks])

        # Generate document title if not provided
        if not document_title:
            document_title = await self.generate_document_title(
                document_text, file_name
            )

        # Generate document summary
        document_summary = await self.generate_document_summary(
            document_text, document_title
        )

        # Process each chunk
        processed_chunks = []
        for i, chunk in enumerate(chunks):
            try:
                # Create contextual header
                contextual_chunk_text = self.create_contextual_header(
                    chunk.page_content, file_name, document_title, document_summary
                )

                # Create new chunk with contextual header
                new_metadata = chunk.metadata.copy()
                new_metadata.update(
                    {
                        "autocontext_enabled": True,
                        "file_name": file_name,
                        "document_title": document_title,
                        "document_summary": (
                            document_summary[:400] + "..."
                            if len(document_summary) > 400
                            else document_summary
                        ),
                        "original_chunk_size": len(chunk.page_content),
                        "contextual_chunk_size": len(contextual_chunk_text),
                    }
                )

                processed_chunk = Document(
                    page_content=contextual_chunk_text, metadata=new_metadata
                )
                processed_chunks.append(processed_chunk)

            except Exception as e:
                logger.error(f"Error processing chunk {i}: {e}")
                # Fall back to original chunk
                processed_chunks.append(chunk)
        logger.info(f"Processed {len(processed_chunks)} chunks")
        return processed_chunks


# Global AutoContext processor instance
autocontext_processor = AutoContextProcessor()


async def apply_autocontext(
    chunks: List[Document],
    document_title: str = None,
    file_name: str = None,
    enabled: bool = True,
) -> List[Document]:
    """
    Apply AutoContext processing to document chunks.

    Args:
        chunks: List of document chunks
        document_title: Optional document title
        file_name: Optional file name for context
        enabled: Whether AutoContext is enabled

    Returns:
        List of processed chunks (with or without contextual headers)
    """
    if not enabled or not chunks:
        return chunks
    try:
        return await autocontext_processor.process_document_chunks(
            chunks, document_title=document_title, file_name=file_name
        )
    except Exception as e:
        logger.error(f"AutoContext processing failed: {e}")
        return chunks  # Return original chunks if processing fails
