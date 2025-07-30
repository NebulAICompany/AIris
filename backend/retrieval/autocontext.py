from typing import List, Dict, Any, Optional
from backend.llm.llm_engine import generate_answer
from backend.core.agents import create_rag_agent
from backend.libs.logger import get_logger
from langchain_core.documents import Document
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
        use_section_summaries: bool = True,
        document_title_guidance: str = None,
        document_summary_guidance: str = None,
        section_summary_guidance: str = None,
    ):
        """
        Initialize the AutoContext processor.

        Args:
            use_document_summary: Whether to generate document-level summaries
            use_section_summaries: Whether to generate section-level summaries
            document_title_guidance: Custom guidance for document title generation
            document_summary_guidance: Custom guidance for document summary generation
            section_summary_guidance: Custom guidance for section summary generation
        """
        self.use_document_summary = use_document_summary
        self.use_section_summaries = use_section_summaries
        self.document_title_guidance = (
            document_title_guidance
            or "Generate a concise, descriptive title for this document"
        )
        self.document_summary_guidance = (
            document_summary_guidance
            or "Provide a brief summary of the document's main content and purpose"
        )
        self.section_summary_guidance = (
            section_summary_guidance or "Summarize the key points of this section"
        )

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
            # Create a simple agent for title generation
            agent = create_rag_agent(
                local_context="",
                web_search_enabled=False,
                query="Generate document title",
                instruction="Generate a concise, descriptive title for the given document",
            )

            title_prompt = f"""You are a document analyst. Generate a concise, descriptive title for the following document.

{self.document_title_guidance}

Document content (first 2000 characters):
{document_text[:2000]}

Requirements:
- Keep the title under 100 characters
- Make it descriptive and specific
- Focus on the main topic or purpose
- Use professional language
- Do not include quotes or special formatting

Generated title:"""

            response = await generate_answer(title_prompt, agent)

            # Clean up the response
            title = response.strip()
            # Remove quotes if present
            title = re.sub(r'^["\']|["\']$', "", title)
            # Limit length
            if len(title) > 100:
                title = title[:97] + "..."

            logger.info(f"Generated document title: {title}")
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
            # Create a simple agent for summary generation
            agent = create_rag_agent(
                local_context="",
                web_search_enabled=False,
                query="Belge özeti oluştur",
                instruction="Belgenin kapsamlı bir özetini oluştur",
            )

            summary_prompt = f"""Bir belge analistisiniz. Aşağıdaki belgenin kapsamlı bir özetini oluşturun.

Belge Başlığı: {document_title}

{self.document_summary_guidance}

Belge içeriği (ilk 4000 karakter):
{document_text[:4000]}

Gereksinimler:
- 2-3 cümlelik bir özet sağlayın
- Ana konulara, amaca ve kilit bilgilere odaklanın
- Kısa ama bilgilendirici olun
- Profesyonel bir dil kullanın
- Alıntı veya özel biçimlendirme kullanmayın

Belge özeti:"""

            response = await generate_answer(summary_prompt, agent)

            # Clean up the response
            summary = response.strip()
            # Remove any quotes
            summary = re.sub(r'^["\']|["\']$', "", summary)

            logger.info(f"Generated document summary: {summary[:100]}...")
            return summary

        except Exception as e:
            logger.error(f"Error generating document summary: {e}")
            return f"This document titled '{document_title}' contains important information."

    def extract_section_hierarchy(self, document_text: str) -> List[Dict[str, Any]]:
        """
        Extract section hierarchy from document text.

        Args:
            document_text: Full document text

        Returns:
            List of section information with hierarchy
        """
        sections = []
        lines = document_text.split("\n")

        # Common section patterns
        section_patterns = [
            r"^(#{1,6})\s+(.+)$",  # Markdown headers
            r"^(.+)\n[=\-]{3,}$",  # Underlined headers
            r"^([A-Z][A-Z\s]+):?\s*$",  # ALL CAPS headers
            r"^(\d+\.?\d*\.?\d*)\s+(.+)$",  # Numbered sections
            r"^([A-Z][a-z\s]+):?\s*$",  # Title case headers
        ]

        current_section = None
        section_content = []

        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            # Check if this line matches any section pattern
            is_section_header = False
            for pattern in section_patterns:
                match = re.match(pattern, line, re.MULTILINE)
                if match:
                    # Save previous section if exists
                    if current_section:
                        current_section["content"] = "\n".join(section_content)
                        current_section["end_line"] = i - 1
                        sections.append(current_section)

                    # Determine header level
                    if pattern.startswith("^(#{1,6})"):
                        level = len(match.group(1))
                        title = match.group(2).strip()
                    elif pattern.startswith("^(.+)\\n[=\\-]"):
                        level = 1 if "=" in lines[i + 1] and i + 1 < len(lines) else 2
                        title = match.group(1).strip()
                    elif pattern.startswith("^([A-Z][A-Z\\s]+)"):
                        level = 1
                        title = match.group(1).strip().rstrip(":")
                    elif pattern.startswith("^(\\d+"):
                        level = match.group(1).count(".") + 1
                        title = match.group(2).strip()
                    else:
                        level = 2
                        title = match.group(1).strip().rstrip(":")

                    # Create new section
                    current_section = {
                        "title": title,
                        "level": level,
                        "start_line": i,
                        "content": "",
                        "end_line": None,
                    }
                    section_content = []
                    is_section_header = True
                    break

            if not is_section_header and current_section:
                section_content.append(line)

        # Add the last section
        if current_section:
            current_section["content"] = "\n".join(section_content)
            current_section["end_line"] = len(lines) - 1
            sections.append(current_section)

        # If no sections found, create a default section
        if not sections:
            sections.append(
                {
                    "title": "Main Content",
                    "level": 1,
                    "start_line": 0,
                    "end_line": len(lines) - 1,
                    "content": document_text,
                }
            )

        logger.info(f"Extracted {len(sections)} sections from document")
        return sections

    async def generate_section_summary(
        self, section_title: str, section_content: str, document_title: str
    ) -> str:
        """
        Generate a summary for a specific section.

        Args:
            section_title: Title of the section
            section_content: Content of the section
            document_title: Title of the document

        Returns:
            Section summary
        """
        if not self.use_section_summaries or not section_content.strip():
            return ""

        try:
            # Create a simple agent for section summary generation
            agent = create_rag_agent(
                local_context="",
                web_search_enabled=False,
                query="Bölüm özeti oluştur",
                instruction="Belge bölümünün özetini oluştur",
            )

            summary_prompt = f"""Bir belge analistisiniz. Lütfen aşağıdaki bölümün kısa ve öz bir özetini oluşturun.

Belge Başlığı: {document_title}
Bölüm Başlığı: {section_title}

{self.section_summary_guidance}

Bölüm içeriği (ilk 2000 karakter):
{section_content[:2000]}

Gereksinimler:
- 1-2 cümlelik bir özet sağlayın
- Bu bölümün ana noktalarına ve amacına odaklanın
- Kısa ama bilgilendirici olun
- Resmi bir dil kullanın
- Alıntı veya özel biçimlendirme kullanmayın

Bölüm özeti:"""

            response = await generate_answer(summary_prompt, agent)

            # Clean up the response
            summary = response.strip()
            # Remove any quotes
            summary = re.sub(r'^["\']|["\']$', "", summary)

            logger.info(
                f"Generated summary for section '{section_title}': {summary[:50]}..."
            )
            return summary

        except Exception as e:
            logger.error(f"Error generating section summary for '{section_title}': {e}")
            return f"This section covers {section_title.lower()}."

    def find_chunk_section(
        self, chunk_text: str, sections: List[Dict[str, Any]], document_lines: List[str]
    ) -> Optional[Dict[str, Any]]:
        """
        Find which section a chunk belongs to.

        Args:
            chunk_text: Text content of the chunk
            sections: List of document sections
            document_lines: Document split into lines

        Returns:
            Section information or None
        """
        # Find the chunk's position in the document
        document_text = "\n".join(document_lines)
        chunk_start = document_text.find(chunk_text.strip())

        if chunk_start == -1:
            # Try to find a partial match
            chunk_words = chunk_text.strip().split()[:10]  # First 10 words
            chunk_start_text = " ".join(chunk_words)
            chunk_start = document_text.find(chunk_start_text)

        if chunk_start == -1:
            return None

        # Convert character position to line number
        chunk_start_line = document_text[:chunk_start].count("\n")

        # Find the section that contains this line
        for section in sections:
            if section["start_line"] <= chunk_start_line <= section["end_line"]:
                return section

        return None

    def create_contextual_header(
        self,
        chunk_text: str,
        document_title: str,
        document_summary: str,
        section_info: Optional[Dict[str, Any]] = None,
        section_summary: str = "",
    ) -> str:
        """
        Create a contextual header for a chunk.

        Args:
            chunk_text: Original chunk text
            document_title: Document title
            document_summary: Document summary
            section_info: Section information
            section_summary: Section summary

        Returns:
            Chunk with contextual header prepended
        """
        header_parts = []

        # Document context
        if document_title:
            header_parts.append(f"Belge: {document_title}")

        if document_summary:
            header_parts.append(f"Belge Özeti: {document_summary}")

        # Section context
        if section_info:
            section_title = section_info.get("title", "")
            if section_title:
                header_parts.append(f"Bölüm: {section_title}")

        if section_summary:
            header_parts.append(f"Bölüm Özeti: {section_summary}")

        # Create the contextual header
        if header_parts:
            contextual_header = "Bağlam: " + " | ".join(header_parts)
            return f"{contextual_header}\n\nİçerik: {chunk_text}"
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

        logger.info(f"Processing {len(chunks)} chunks with AutoContext")

        # Reconstruct document text from chunks
        document_text = "\n\n".join([chunk.page_content for chunk in chunks])
        document_lines = document_text.split("\n")

        # Generate document title if not provided
        if not document_title:
            document_title = await self.generate_document_title(
                document_text, file_name
            )

        # Generate document summary
        document_summary = await self.generate_document_summary(
            document_text, document_title
        )

        # Extract section hierarchy
        sections = self.extract_section_hierarchy(document_text)

        # Generate section summaries
        section_summaries = {}
        if self.use_section_summaries:
            for section in sections:
                section_key = f"{section['title']}_{section['level']}"
                section_summaries[section_key] = await self.generate_section_summary(
                    section["title"], section["content"], document_title
                )

        # Process each chunk
        processed_chunks = []
        for i, chunk in enumerate(chunks):
            try:
                # Find the section this chunk belongs to
                section_info = self.find_chunk_section(
                    chunk.page_content, sections, document_lines
                )

                # Get section summary if available
                section_summary = ""
                if section_info:
                    section_key = f"{section_info['title']}_{section_info['level']}"
                    section_summary = section_summaries.get(section_key, "")

                # Create contextual header
                contextual_chunk_text = self.create_contextual_header(
                    chunk.page_content,
                    document_title,
                    document_summary,
                    section_info,
                    section_summary,
                )

                # Create new chunk with contextual header
                new_metadata = chunk.metadata.copy()
                new_metadata.update(
                    {
                        "autocontext_enabled": True,
                        "document_title": document_title,
                        "document_summary": (
                            document_summary[:200] + "..."
                            if len(document_summary) > 200
                            else document_summary
                        ),
                        "section_title": section_info["title"] if section_info else "",
                        "section_level": section_info["level"] if section_info else 0,
                        "section_summary": (
                            section_summary[:200] + "..."
                            if len(section_summary) > 200
                            else section_summary
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

        logger.info(
            f"Successfully processed {len(processed_chunks)} chunks with AutoContext"
        )
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
            chunks, document_title, file_name
        )
    except Exception as e:
        logger.error(f"AutoContext processing failed: {e}")
        return chunks  # Return original chunks if processing fails
