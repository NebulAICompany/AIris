from typing import List, Tuple, Optional
from backend.shared.logger import get_logger
from backend.shared.constants import OPENAI_MODEL
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage
from datetime import datetime
import os
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

    async def generate_document_context(
        self, document_text: str, document_title: str, file_path: str = None
    ) -> Tuple[str, Optional[str]]:
        """
        Generate summary AND extract date in one LLM call for efficiency.
        Falls back to file modification date if no date found in content.
        
        Args:
            document_text: Full text of the document
            document_title: Title of the document
            file_path: Optional file path for fallback date

        Returns:
            Tuple of (document_summary, document_date)
        """
        default_summary = f"This document titled '{document_title}' contains important information."
        document_date = None
        
        if not self.use_document_summary:
            return "", self._get_file_date(file_path)

        try:
            context_prompt = f"""You are a document analyst. Analyze this document and provide:
1. A 2-3 sentence summary focusing on main topics and key information
2. The most relevant date (publication date, report date, effective date, or date range like Q3 2024)

Document Title: {document_title}

Document content (first 4000 characters):
{document_text[:4000]}

Requirements:
- Write in the language of the document
- For dates: use YYYY-MM-DD format. For quarters use range (e.g., "2024-07-01 to 2024-09-30")
- If only year/month mentioned, use first day (e.g., March 2024 → 2024-03-01)
- If no date found, write NO_DATE

Respond in EXACTLY this format (no extra text):
SUMMARY: <your summary here>
DATE: <YYYY-MM-DD or date range or NO_DATE>"""

            response = await OPENAI_MODEL.ainvoke([HumanMessage(content=context_prompt)])
            content = response.content.strip()

            # Parse response
            summary = default_summary
            if "SUMMARY:" in content:
                summary_match = re.search(r'SUMMARY:\s*(.+?)(?=DATE:|$)', content, re.DOTALL)
                if summary_match:
                    summary = summary_match.group(1).strip()
                    summary = re.sub(r'^["\']|["\']$', "", summary)
            
            if "DATE:" in content:
                date_match = re.search(r'DATE:\s*(.+?)$', content, re.MULTILINE)
                if date_match:
                    date_str = date_match.group(1).strip()
                    if date_str and date_str != "NO_DATE":
                        document_date = date_str

            # Fallback to file date if no date extracted
            if not document_date:
                document_date = self._get_file_date(file_path)

            return summary, document_date

        except Exception as e:
            logger.error(f"Error generating document context: {e}")
            return default_summary, self._get_file_date(file_path)

    def _get_file_date(self, file_path: str) -> Optional[str]:
        """Get file modification date as fallback."""
        if file_path and os.path.exists(file_path):
            try:
                mtime = os.path.getmtime(file_path)
                return f"{datetime.fromtimestamp(mtime).strftime('%Y-%m-%d')} (file date)"
            except Exception as e:
                logger.warning(f"Error getting file date: {e}")
        return None

    def create_contextual_header(
        self,
        chunk_text: str,
        file_name: str = None,
        document_title: str = None,
        document_summary: str = None,
        document_date: str = None,
    ) -> str:
        """
        Create a contextual header for a chunk.
        """
        header_parts = []

        if file_name:
            header_parts.append(f"File: {file_name}")
        if document_title:
            header_parts.append(f"Document: {document_title}")
        if document_date:
            header_parts.append(f"Date: {document_date}")
        if document_summary:
            header_parts.append(f"Summary: {document_summary}")

        if header_parts:
            contextual_header = "Context: " + " | ".join(header_parts)
            return f"{contextual_header}\n\nContent: {chunk_text}"
        return chunk_text

    async def process_document_chunks(
        self, chunks: List[Document], document_title: str = None, 
        file_name: str = None, file_path: str = None
    ) -> List[Document]:
        """
        Process document chunks to add contextual headers.
        """
        if not chunks:
            return chunks

        document_text = "\n\n".join([chunk.page_content for chunk in chunks])

        if not document_title:
            document_title = await self.generate_document_title(document_text, file_name)

        # Generate summary and extract date in one LLM call
        document_summary, document_date = await self.generate_document_context(
            document_text, document_title, file_path
        )

        processed_chunks = []
        for i, chunk in enumerate(chunks):
            try:
                contextual_chunk_text = self.create_contextual_header(
                    chunk.page_content, file_name, document_title, 
                    document_summary, document_date
                )

                new_metadata = chunk.metadata.copy()
                new_metadata.update({
                    "autocontext_enabled": True,
                    "file_name": file_name,
                    "document_title": document_title,
                    "document_date": document_date,
                    "document_summary": (
                        document_summary[:400] + "..."
                        if len(document_summary) > 400 else document_summary
                    ),
                    "original_chunk_size": len(chunk.page_content),
                    "contextual_chunk_size": len(contextual_chunk_text),
                })

                processed_chunks.append(Document(
                    page_content=contextual_chunk_text, metadata=new_metadata
                ))
            except Exception as e:
                logger.error(f"Error processing chunk {i}: {e}")
                processed_chunks.append(chunk)
                
        logger.info(f"Processed {len(processed_chunks)} chunks with date: {document_date}")
        return processed_chunks


# Global AutoContext processor instance
autocontext_processor = AutoContextProcessor()


async def apply_autocontext(
    chunks: List[Document],
    document_title: str = None,
    file_name: str = None,
    file_path: str = None,
    enabled: bool = True,
) -> List[Document]:
    """
    Apply AutoContext processing to document chunks.
    """
    if not enabled or not chunks:
        return chunks
    try:
        return await autocontext_processor.process_document_chunks(
            chunks, document_title=document_title, 
            file_name=file_name, file_path=file_path
        )
    except Exception as e:
        logger.error(f"AutoContext processing failed: {e}")
        return chunks
