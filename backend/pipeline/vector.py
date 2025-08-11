from qdrant_client import QdrantClient, models
from langchain_openai.embeddings import OpenAIEmbeddings
from langchain_experimental.text_splitter import SemanticChunker
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from backend.security.pii import mask_text
from typing import List
import time
import asyncio
from enum import Enum
from backend.retrieval.autocontext import apply_autocontext
from backend.shared.constants import VECTORSTORE_PATH_STR
from backend.shared.logger import get_logger

logger = get_logger("VECTOR_PIPELINE")


class PreEmbeddingProcess(Enum):
    """Enum for pre-embedding process options"""

    NONE = "none"
    CCH = "cch"  # Contextual Chunk Headers (AutoContext)
    PDR = "pdr"  # Parent Document Retrieval (PDR)

class VectorStorePipeline:
    """
    Enhanced Vector Store Pipeline with configurable pre-embedding processing
    Supports: None and CCH (Contextual Chunk Headers)
    """

    def __init__(
        self, pre_embedding_process: PreEmbeddingProcess = PreEmbeddingProcess.NONE
    ):
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        self.text_splitter = SemanticChunker(
            self.embeddings,
            breakpoint_threshold_type="percentile",
            breakpoint_threshold_amount=80,

        )
        self.pre_embedding_process = pre_embedding_process

    def create_parent_child_documents(
        self, original_docs: List[Document], file_name: str
    ) -> List[Document]:
        """
        Create parent-child documents 
        """
        parent_child_docs = []
        recursive_text_splitter = RecursiveCharacterTextSplitter(chunk_size=100, chunk_overlap=20)
        for doc in original_docs:
            parent_child_docs.append(doc)
            chunks = recursive_text_splitter.split_text(doc.page_content)
            for chunk in chunks:
                parent_child_docs.append(Document(page_content=chunk, metadata={
                    **doc.metadata,
                    "content_type": "child",
                    "parent_chunk_id": doc.metadata.get("chunk_id"),
                    "parent_content": doc.page_content,
                    "file_name": file_name,
                }))

        return parent_child_docs

    def apply_pre_embedding_process(
        self, docs: List[Document], file_name: str
    ) -> List[Document]:
        """
        Apply the selected pre-embedding process to the documents
        """
        if self.pre_embedding_process == PreEmbeddingProcess.NONE:
            logger.info(f"📝 No pre-embedding processing applied to {file_name}")
            return docs

        elif self.pre_embedding_process == PreEmbeddingProcess.CCH:
            logger.info(f"🔗 Applying Contextual Chunk Headers (AutoContext) to {file_name}...")
            try:
                # Handle event loop properly for async AutoContext processing
                def run_autocontext():
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            # If loop is already running, create a new thread
                            import concurrent.futures

                            with concurrent.futures.ThreadPoolExecutor() as executor:
                                future = executor.submit(
                                    lambda: asyncio.run(
                                        apply_autocontext(
                                            docs, file_name=file_name, enabled=True
                                        )
                                    )
                                )
                                return future.result()
                        else:
                            return loop.run_until_complete(
                                apply_autocontext(
                                    docs, file_name=file_name, enabled=True
                                )
                            )
                    except RuntimeError:
                        # No event loop exists, create a new one
                        return asyncio.run(
                            apply_autocontext(docs, file_name=file_name, enabled=True)
                        )

                processed_docs = run_autocontext()
                logger.info(
                    f"✅ Contextual Chunk Headers applied to {len(processed_docs)} chunks"
                )
                return processed_docs

            except Exception as e:
                logger.warning(f"⚠️ AutoContext processing failed for {file_name}: {e}")
                logger.warning("   Continuing with original chunks...")
                return docs
        elif self.pre_embedding_process == PreEmbeddingProcess.PDR:
            logger.info(
                f"❓ Applying PDR (Personalized Document Retrieval) to {file_name}..."
            )
            parent_child_docs = self.create_parent_child_documents(docs, file_name)
            return parent_child_docs
        else:
            logger.warning(f"⚠️ Unknown pre-embedding process: {self.pre_embedding_process}")
            return docs

    async def run(self, text_content: str, document_name: str):
        """
        Process text content directly without reading from files
        
        Args:
            text_content: The extracted text content from parser
            document_name: Name of the document (for metadata)
        """
        start_time = time.time()

        try:
            if not text_content or not text_content.strip():
                logger.error("❌ No valid text content provided")
                return

            chunk_idx = 0

            logger.info(f"🚀 Processing text content with pre-embedding process: {self.pre_embedding_process.value}")
            logger.info(f"📖 Processing {len(text_content)} characters from {document_name}")

            # Split the text into semantic chunks
            logger.info(f"✂️ Splitting {document_name} into semantic chunks...")
            docs = self.text_splitter.create_documents([text_content])
            if not docs:
                logger.warning(f"⚠️ Warning: No chunks were created for {document_name}.")
                return

            logger.info(f"✅ Document '{document_name}' split into {len(docs)} semantic chunks")

            # Add basic metadata to original chunks
            for doc in docs:
                if not hasattr(doc, "metadata") or doc.metadata is None:
                    doc.metadata = {}
                doc.metadata["chunk_id"] = f"chunk_{chunk_idx}"
                doc.metadata["file_name"] = f"{document_name}"  # Keep compatibility with existing code
                doc.metadata["content_type"] = "original"
                doc.metadata["contains_image"] = False
                
                if '(Image)' in doc.page_content:
                    doc.metadata["contains_image"] = True
                
                chunk_idx += 1

            logger.info(f"🔍 {len(docs)} documents before pre-embedding process")
            # Apply selected pre-embedding process
            processed_docs = self.apply_pre_embedding_process(docs, document_name)
            logger.info(f"✅ {len(processed_docs)} documents processed")

            # Apply PII masking to processed documents in batches
            await self._apply_pii_masking(processed_docs, document_name)

            logger.info(f"🗄️ Adding {len(processed_docs)} documents to vectorstore...")
            client = QdrantClient(path=VECTORSTORE_PATH_STR)
            if not client.collection_exists(collection_name="test_collection"):
                client.create_collection(
                    collection_name="test_collection",
                    vectors_config=models.VectorParams(size=1536, distance=models.Distance.COSINE),
                )
                logger.info("Collection created")
            else:
                logger.info("Collection already exists")

            # Create embeddings in batches for better performance
            await self._create_and_upload_embeddings(client, processed_docs)

            client.close()

            logger.info(f"📈 Total text processed: {len(text_content)} characters")

            # Log processing time
            processing_time = time.time() - start_time
            logger.info(f"⏱️ Processing completed in {processing_time:.2f} seconds")

        except Exception as e:
            logger.error(f"❌ Error in vector store processing: {str(e)}")
            raise e

    async def _create_and_upload_embeddings(self, client: QdrantClient, processed_docs: List[Document]):
        """
        Create embeddings in batches and upload to Qdrant for better performance
        """
        batch_size = 10
        logger.info(f"🔄 Creating embeddings for {len(processed_docs)} documents in batches of {batch_size}...")

        all_points = []

        for i in range(0, len(processed_docs), batch_size):
            batch_docs = processed_docs[i:i + batch_size]
            logger.info(f"⚡ Processing embedding batch {i//batch_size + 1}/{(len(processed_docs) + batch_size - 1)//batch_size} ({len(batch_docs)} documents)")

            # Extract text content for batch embedding
            batch_texts = [doc.page_content for doc in batch_docs]

            # Create embeddings for the batch
            try:
                # Use embed_documents for batch processing instead of embed_query for single documents
                batch_embeddings = await asyncio.to_thread(
                    self.embeddings.embed_documents, batch_texts
                )

                # Create points for this batch
                for idx, (doc, embedding) in enumerate(zip(batch_docs, batch_embeddings)):
                    point = models.PointStruct(
                        id=i + idx,
                        vector=embedding,
                        payload={
                            "page_content": doc.page_content,
                            "metadata": doc.metadata,
                        },
                    )
                    all_points.append(point)

            except Exception as e:
                logger.error(f"❌ Error creating embeddings for batch {i//batch_size + 1}: {str(e)}")
                # Fallback to individual embedding creation for this batch
                logger.info("🔄 Falling back to individual embedding creation...")
                for idx, doc in enumerate(batch_docs):
                    try:
                        embedding = await asyncio.to_thread(
                            self.embeddings.embed_query, doc.page_content
                        )
                        point = models.PointStruct(
                            id=i + idx,
                            vector=embedding,
                            payload={
                                "page_content": doc.page_content,
                                "metadata": doc.metadata,
                            },
                        )
                        all_points.append(point)
                    except Exception as individual_error:
                        logger.error(f"❌ Error creating embedding for document {i + idx}: {str(individual_error)}")
                        continue

        # Upload all points to Qdrant
        if all_points:
            logger.info(f"📤 Uploading {len(all_points)} points to vectorstore...")
            client.upload_points(
                collection_name="test_collection",
                points=all_points,
            )
            logger.info(f"✅ Successfully uploaded {len(all_points)} points to vectorstore")
        else:
            logger.warning("⚠️ No points to upload to vectorstore")

    async def _apply_pii_masking(self, processed_docs: List[Document], document_name: str):
        """
        Apply PII masking to processed documents in batches
        """
        logger.info(f"🔒 Applying PII masking to {len(processed_docs)} documents...")

        doc_contents = [doc.page_content for doc in processed_docs]

        batch_size = 5
        masked_contents = []

        for i in range(0, len(doc_contents), batch_size):
            batch_group = doc_contents[i:i + batch_size]
            logger.info(f"🔒 Processing PII batch group {i//batch_size + 1}/{(len(doc_contents) + batch_size - 1)//batch_size} ({len(batch_group)} documents)")

            masked_group = await mask_text(batch_group, f"{document_name}_batch_{i//batch_size + 1}")
            masked_contents.extend(masked_group)

        logger.info(f"✅ PII masking completed for all {len(processed_docs)} documents in {(len(doc_contents) + batch_size - 1)//batch_size} groups")

        # Update documents with masked content
        for i, doc in enumerate(processed_docs):
            doc.page_content = masked_contents[i]
