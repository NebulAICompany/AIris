from qdrant_client import AsyncQdrantClient, models
from langchain_text_splitters import RecursiveCharacterTextSplitter, Language
from langchain_core.documents import Document
from backend.retrieval.autocontext import apply_autocontext
from backend.retrieval.keyword_search import get_keyword_search
from backend.retrieval.retriever import load_vectorstore
from backend.shared.constants import VECTORSTORE_PATH_STR, co, IMAGES_PATH_STR
from backend.utils.parser import embed_image_with_caption
from backend.shared.logger import get_logger
from backend.security.pii import mask_text
from typing import List
from enum import Enum
import asyncio
import tiktoken
import hashlib
import os
import re
logger = get_logger("VECTOR_PIPELINE")
enc = tiktoken.get_encoding("cl100k_base")


async def generate_embeddings(texts: List[str]) -> List[List[float]]:
    """Embed texts with Cohere embed-v4.0 (search_document, 1536-dim), with batching and rate-limit retries."""
    if not texts:
        return []

    def _embed_batch(batch_texts: List[str]) -> List[List[float]]:
        if not co:
            raise RuntimeError("Cohere client not initialised")
        embed_input = [
            {"content": [{"type": "text", "text": t}]} for t in batch_texts
        ]
        return co.embed(
            inputs=embed_input,
            model="embed-v4.0",
            input_type="search_document",
            output_dimension=1536,
            embedding_types=["float"],
        ).embeddings.float

    batch_size = 8
    all_embeddings: List[List[float]] = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        for attempt in range(13):
            try:
                batch_embs = await asyncio.to_thread(_embed_batch, batch)
                break
            except Exception as e:
                if "rate limit" in str(e).lower() and attempt < 12:
                    logger.warning(
                        "Embed rate limit hit, retrying in 5s... (attempt %s/13)",
                        attempt + 1,
                    )
                    await asyncio.sleep(5)
                else:
                    raise
        all_embeddings.extend(batch_embs)

    return all_embeddings


class PreEmbeddingProcess(Enum):
    """Enum for pre-embedding process options"""

    NONE = "none"
    CCH = "cch"  # Contextual Chunk Headers (AutoContext)


class VectorStorePipeline:
    """
    Enhanced Vector Store Pipeline with configurable pre-embedding processing
    Supports: None and CCH (Contextual Chunk Headers)
    """

    class Embedding:
        """Handles text and image embedding operations"""

        @staticmethod
        async def upload_text_embed(
            client: AsyncQdrantClient, processed_docs: List[Document]
        ):
            """Create embeddings and upload text chunks to Qdrant."""
            if not processed_docs:
                logger.warning("No documents to embed.")
                return

            texts = [doc.page_content for doc in processed_docs]
            logger.info(
                "Processing %s chunk(s) with Cohere embed-v4.0...",
                len(texts),
            )

            embeddings = await generate_embeddings(texts)

            if len(embeddings) != len(processed_docs):
                raise ValueError(
                    "Embedding count (%s) != doc count (%s)"
                    % (len(embeddings), len(processed_docs))
                )

            all_points = []
            for idx, (doc, embedding) in enumerate(
                zip(processed_docs, embeddings)
            ):
                if "[Table ID:table_" in doc.page_content:
                    doc.metadata["contains_image"] = True
                    doc.metadata["figure_id"] = doc.page_content.split(
                        "[Table ID:"
                    )[1].split("]")[0]
                    doc.metadata["image_path"] = os.path.join(
                        IMAGES_PATH_STR,
                        doc.metadata["figure_id"] + ".png",
                    )
                content_hash = hashlib.md5(doc.page_content.encode()).hexdigest()
                point_id = int(content_hash[:15], 16) + idx
                all_points.append(
                    models.PointStruct(
                        id=point_id,
                        vector=embedding,
                        payload={
                            "page_content": doc.page_content,
                            "metadata": doc.metadata,
                        },
                    )
                )

            await client.upsert(
                collection_name="documents",
                points=all_points,
                wait=True,
            )
            logger.info(
                "Successfully uploaded %s points to vectorstore",
                len(all_points),
            )

        @staticmethod
        async def upload_images_embed(
            client: AsyncQdrantClient,
            figure_images: dict,
            document_name: str,
            keyword_search,
        ):
            """Create embeddings and upload images to Qdrant and keyword search"""
            try:
                logger.info(
                    f"Embedding {len(figure_images)} images for {document_name}"
                )
                image_points = []

                batch_size = 10
                figure_items = list(figure_images.items())
                total_batches = (len(figure_items) + batch_size - 1) // batch_size

                for i in range(0, len(figure_items), batch_size):
                    batch = figure_items[i : i + batch_size]
                    batch_num = i // batch_size + 1
                    logger.info(
                        f"Processing image batch {batch_num}/{total_batches} ({len(batch)} images)"
                    )

                    for figure_id, image_data in batch:
                        try:
                            image_bytes = image_data.get("image_bytes")
                            caption = image_data.get("caption", "")

                            embedding = embed_image_with_caption(
                                image_bytes, caption, figure_id
                            )

                            if embedding:
                                page_number = image_data.get("page_number")
                                figure_label = (
                                    f"**[{caption} ID:{figure_id}]**"
                                    if caption
                                    else f"**[Figure ID:{figure_id}]**"
                                )
                                header_parts = [f"File: {document_name}"]
                                if page_number is not None:
                                    header_parts.append(f"Page: {page_number}")
                                context_header = "Context: " + " | ".join(header_parts)
                                page_content = f"{context_header}\n\nContent: {figure_label}"
                                metadata = {
                                    "content_type": "image",
                                    "figure_id": figure_id,
                                    "caption": caption,
                                    "file_name": document_name,
                                    "image_path": image_data.get("image_path", ""),
                                    "contains_image": True,
                                    "page_number": page_number,
                                }

                                hash_obj = hashlib.sha256(figure_id.encode("utf-8"))
                                point_id = int.from_bytes(
                                    hash_obj.digest()[:8], byteorder="big"
                                )

                                point = models.PointStruct(
                                    id=point_id,
                                    vector=embedding,
                                    payload={
                                        "metadata": metadata,
                                        "page_content": page_content,
                                    },
                                )
                                image_points.append(point)
                                logger.info(f"Added image in {document_name} with figure id {figure_id} to vectorstore")
                                # Add to keyword search
                                keyword_search.add_document(
                                    figure_id, page_content, metadata
                                )
                            else:
                                logger.warning(f"Failed to embed image {figure_id}")

                        except Exception as e:
                            logger.error(f"Error embedding image {figure_id}: {e}")
                            continue

                await client.upsert(
                    collection_name="documents",
                    points=image_points,
                    wait=True,
                )
                logger.info(
                    f"Successfully uploaded {len(image_points)} image embeddings to vectorstore"
                )

                keyword_search.save_index()

            except Exception as e:
                logger.error(f"Error embedding and storing images: {e}")

    def __init__(
        self, pre_embedding_process: PreEmbeddingProcess = PreEmbeddingProcess.NONE
    ):
        self.text_splitter = RecursiveCharacterTextSplitter.from_language(
            Language.MARKDOWN,
            chunk_size=1000,
            chunk_overlap=250,
            length_function=self.length_function,
        )
        self.pre_embedding_process = pre_embedding_process

    def length_function(self, text: str) -> int:
        return len(enc.encode(text))

    def apply_pre_embedding_process(
        self, docs: List[Document], file_name: str, file_path: str = None
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
                def run_autocontext():
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            import concurrent.futures
                            with concurrent.futures.ThreadPoolExecutor() as executor:
                                future = executor.submit(
                                    lambda: asyncio.run(apply_autocontext(
                                        docs, file_name=file_name, file_path=file_path, enabled=True
                                    )))
                                return future.result()
                        else:
                            return loop.run_until_complete(
                                apply_autocontext(docs, file_name=file_name, file_path=file_path, enabled=True)
                            )
                    except RuntimeError:
                        return asyncio.run(apply_autocontext(
                            docs, file_name=file_name, file_path=file_path, enabled=True
                        ))

                processed_docs = run_autocontext()
                logger.info(
                    f"✅ Contextual Chunk Headers applied to {len(processed_docs)} chunks"
                )
                return processed_docs

            except Exception as e:
                logger.warning(f"⚠️ AutoContext processing failed for {file_name}: {e}")
                return docs
        else:
            logger.warning(
                f"⚠️ Unknown pre-embedding process: {self.pre_embedding_process}"
            )
            return docs

    async def run(self, text_content: str, document_name: str, 
                   file_extension: str = None, file_path: str = None, figure_images: dict = None):
        """
        Process text content directly without reading from files

        Args:
            text_content: The extracted text content from parser
            document_name: Name of the document (for metadata)
            file_extension: Extension of the document
            figure_images: Dictionary of figure images with their captions and image bytes
            file_path: Original file path for date extraction fallback
        """
        try:
            if not text_content or not text_content.strip():
                logger.error("❌ No valid text content provided")
                return

            chunk_idx = 0

            if file_extension == ".xlsx" or file_extension == ".xls":
                text_content_list = text_content.split("====SHEET SEPARATOR====")
                docs = self.text_splitter.create_documents(text_content_list)
            else:
                docs = self.text_splitter.create_documents([text_content])
            if not docs:
                logger.warning(
                    f"⚠️ Warning: No chunks were created for {document_name}."
                )
                return

            logger.info(
                f"   ✅ Document '{document_name}' split into {len(docs)} chunks"
            )
            _PAGE_MARKER = re.compile(r"<!-- PAGE_BREAK:(\d+) -->")
            current_page = 1

            for doc in docs:
                if not hasattr(doc, "metadata") or doc.metadata is None:
                    doc.metadata = {}
                first_marker = _PAGE_MARKER.search(doc.page_content)
                if first_marker is None:
                    doc.metadata["page_number"] = current_page
                else:
                    pre_marker = doc.page_content[: first_marker.start()].strip()
                    doc.metadata["page_number"] = (
                        current_page if pre_marker else int(first_marker.group(1))
                    )
                    all_markers = _PAGE_MARKER.findall(doc.page_content)
                    current_page = int(all_markers[-1])

                doc.page_content = _PAGE_MARKER.sub("", doc.page_content).strip()
                doc.metadata["chunk_id"] = f"chunk_{chunk_idx}"
                doc.metadata["file_name"] = f"{document_name}"
                chunk_idx += 1

            # Apply selected pre-embedding process with file_path for date extraction
            processed_docs = self.apply_pre_embedding_process(docs, document_name, file_path)
            logger.info(f"✅ {len(processed_docs)} documents processed")

            # Apply PII masking to processed documents in batches
            logger.info("Applying PII masking...")
            await self._apply_pii_masking(processed_docs, document_name)
            logger.info("PII masking complete")

            client = await load_vectorstore(VECTORSTORE_PATH_STR)

            if not await client.collection_exists(collection_name="documents"):
                await client.create_collection(
                    collection_name="documents",
                    vectors_config=models.VectorParams(
                        size=1536, distance=models.Distance.COSINE
                    ),
                )
            else:
                logger.info("Collection already exists")

            logger.info("Creating embeddings using Cohere embed-v4.0...")
            await self.Embedding.upload_text_embed(client, processed_docs)
            logger.info("All text embeddings created and uploaded")

            logger.info("Building keyword search index...")
            keyword_search = get_keyword_search()

            # Remove any existing documents from the same file first
            keyword_search.remove_documents_by_file(document_name)

            for idx, doc in enumerate(processed_docs):
                doc_id = f"{document_name}_{doc.metadata.get('chunk_id', idx)}"
                keyword_search.add_document(doc_id, doc.page_content, doc.metadata)

            # Save keyword search index
            keyword_search.save_index()
            if figure_images:
                logger.info(f"Embedding {len(figure_images)} image(s) with captions...")
                await self.Embedding.upload_images_embed(
                    client, figure_images, document_name, keyword_search
                )
                logger.info("Image embeddings complete")

        except Exception as e:
            logger.error(f"❌ Error in vector store processing: {str(e)}")
            raise e

    async def _apply_pii_masking(
        self, processed_docs: List[Document], document_name: str
    ):
        """
        Apply PII masking to processed documents in batches
        Handles documents larger than 5120 characters by splitting them
        """
        MAX_CHARS = 5120
        doc_contents = [doc.page_content for doc in processed_docs]
        
        # Track which documents need splitting and their split parts
        split_mapping = []  # List of (original_index, start_position, [split_parts])
        contents_to_mask = []
        
        for idx, content in enumerate(doc_contents):
            if len(content) > MAX_CHARS:
                # Split large document into chunks
                split_parts = []
                for i in range(0, len(content), MAX_CHARS):
                    split_parts.append(content[i:i + MAX_CHARS])
                split_mapping.append((idx, len(contents_to_mask), split_parts))
                contents_to_mask.extend(split_parts)
                logger.info(f"📄 Document {idx} split into {len(split_parts)} parts for pii mask(original size: {len(content)} chars)")
            else:
                split_mapping.append((idx, len(contents_to_mask), [content]))
                contents_to_mask.append(content)

        batch_size = 5
        masked_contents = []

        for i in range(0, len(contents_to_mask), batch_size):
            batch_group = contents_to_mask[i : i + batch_size]
            masked_group = await mask_text(
                batch_group, f"{document_name}_batch_{i//batch_size + 1}"
            )
            masked_contents.extend(masked_group)

        # Reconstruct documents by combining split parts
        final_masked_contents = []
        for orig_idx, start_pos, split_parts in split_mapping:
            if len(split_parts) > 1:
                # Recombine split parts
                combined = "".join(masked_contents[start_pos:start_pos + len(split_parts)])
                final_masked_contents.append(combined)
            else:
                final_masked_contents.append(masked_contents[start_pos])

        # Update documents with masked content
        for i, doc in enumerate(processed_docs):
            doc.page_content = final_masked_contents[i]
