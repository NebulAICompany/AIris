import os
from langchain_experimental.text_splitter import SemanticChunker
from langchain_openai.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from backend.guardrails.pii import mask_text
from openai import OpenAI
from pathlib import Path
from typing import List, Dict
import time
import asyncio
from enum import Enum
from backend.monitoring.metrics import (
    hype_hypothetical_content_generated,
    hype_enhanced_documents_indexed,
    vectorstore_total_chunks,
)
from backend.retrieval.autocontext import apply_autocontext
from dotenv import load_dotenv


load_dotenv()


class PreEmbeddingProcess(Enum):
    """Enum for pre-embedding process options"""

    NONE = "none"
    HYPE = "hype"
    CCH = "cch"  # Contextual Chunk Headers (AutoContext)


class VectorStorePipeline:
    """
    Enhanced Vector Store Pipeline with configurable pre-embedding processing
    Supports: None, HyPE (Hypothetical Prompt Embeddings), and CCH (Contextual Chunk Headers)
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
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


    def generate_hypothetical_prompts(
        self, original_chunk: str, chunk_metadata: Dict
    ) -> List[str]:
        """
        Generate hypothetical prompts/queries that users might ask to find this document chunk
        """

        system_prompt = """Sen bir finansal belge analisti ve soru üretim uzmanısın. 
                    Verilen belge parçası için kullanıcıların sorabileceği hipotetik sorular üret.
                    Sorular finansal terimler, sayısal veriler ve analiz odaklı olmalı."""

        user_prompt = f"""Belge içeriği:
{original_chunk}

Bu belge içeriği için kullanıcıların sorabileceği 3 farklı hipotetik soru/sorgu üret:"""

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=800,
            temperature=0.8,
        )

        generated_text = response.choices[0].message.content.strip()

        hypothetical_prompts = [
            prompt.strip()
            for prompt in generated_text.split("|||")
            if prompt.strip() and len(prompt.strip()) > 10
        ]

        # Limit to 3 hypothetical prompts per chunk
        hypothetical_prompts = hypothetical_prompts[:3]

        # Update metrics
        hype_hypothetical_content_generated.inc(len(hypothetical_prompts))

        print(
            f"❓ Generated {len(hypothetical_prompts)} hypothetical prompts for chunk"
        )
        for i, prompt in enumerate(hypothetical_prompts[:3]):  # Show first 3
            print(f"   {i+1}. {prompt}")

        return hypothetical_prompts

    def create_enhanced_documents(
        self, original_docs: List[Document], file_name: str
    ) -> List[Document]:
        """
        Create enhanced document set with original content + hypothetical prompts as separate searchable documents
        """
        enhanced_docs = []

        for i, doc in enumerate(original_docs):
            # Add original document
            enhanced_docs.append(doc)
            hype_enhanced_documents_indexed.labels(content_type="original").inc()

            # Generate hypothetical prompts for this chunk
            hypothetical_prompts = self.generate_hypothetical_prompts(
                doc.page_content, {"file_name": file_name}
            )

            # Create separate documents for each hypothetical prompt
            # These prompt documents will be searchable and point back to the original content
            for j, hyp_prompt in enumerate(hypothetical_prompts):
                # Create a document that contains the prompt but references the original content
                prompt_doc = Document(
                    page_content=f"{hyp_prompt}\n\n[Bu soru aşağıdaki içerikle ilgilidir:]\n{doc.page_content}",
                    metadata={
                        **doc.metadata,
                        "content_type": "hypothetical_prompt",
                        "original_chunk_id": doc.metadata.get("chunk_id"),
                        "prompt_index": j,
                        "hypothetical_prompt": hyp_prompt,
                        "original_content": doc.page_content,
                        "file_name": file_name,
                    },
                )
                enhanced_docs.append(prompt_doc)
                hype_enhanced_documents_indexed.labels(
                    content_type="hypothetical_prompt"
                ).inc()

            # Add small delay to avoid rate limiting
            time.sleep(0.1)

        return enhanced_docs

    def apply_pre_embedding_process(
        self, docs: List[Document], file_name: str
    ) -> List[Document]:
        """
        Apply the selected pre-embedding process to the documents
        """
        if self.pre_embedding_process == PreEmbeddingProcess.NONE:
            print(f"📝 No pre-embedding processing applied to {file_name}")
            return docs

        elif self.pre_embedding_process == PreEmbeddingProcess.CCH:
            print(
                f"🔗 Applying Contextual Chunk Headers (AutoContext) to {file_name}..."
            )
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
                print(
                    f"✅ Contextual Chunk Headers applied to {len(processed_docs)} chunks"
                )
                return processed_docs

            except Exception as e:
                print(f"⚠️ AutoContext processing failed for {file_name}: {e}")
                print("   Continuing with original chunks...")
                return docs

        elif self.pre_embedding_process == PreEmbeddingProcess.HYPE:
            print(
                f"❓ Applying HyPE (Hypothetical Prompt Embeddings) to {file_name}..."
            )
            try:
                enhanced_docs = self.create_enhanced_documents(docs, file_name)
                prompt_count = len(enhanced_docs) - len(docs)

                print(
                    f"✅ HyPE applied: {prompt_count} times total"
                )
                return enhanced_docs

            except Exception as e:
                print(f"⚠️ HyPE processing failed for {file_name}: {e}")
                print("   Continuing with original chunks...")
                return docs

        else:
            print(f"⚠️ Unknown pre-embedding process: {self.pre_embedding_process}")
            return docs

    def run(self, text_content: str, document_name: str, save_path: str):
        """
        Process text content directly without reading from files
        
        Args:
            text_content: The extracted text content from parser
            document_name: Name of the document (for metadata)
            save_path: Path to save the vector store
        """
        start_time = time.time()

        try:
            if not text_content or not text_content.strip():
                print("❌ No valid text content provided")
                return

            chunk_idx = 0

            # Ensure save_path exists
            os.makedirs(save_path, exist_ok=True)
            vectorstore_path = save_path

            # Load or create vectorstore
            if os.path.exists(os.path.join(vectorstore_path, "index.faiss")):
                print("Loading existing vector store...")
                vectorstore = FAISS.load_local(
                    vectorstore_path,
                    self.embeddings,
                    allow_dangerous_deserialization=True,
                )
                print(f"Loaded {vectorstore.index.ntotal} existing chunks")
            else:
                print("Creating new vector store...")
                vectorstore = None

            print(f"🚀 Processing text content with pre-embedding process: {self.pre_embedding_process.value}")
            print(f"📖 Processing {len(text_content)} characters from {document_name}")

            # Split the text into semantic chunks
            print(f"✂️ Splitting {document_name} into semantic chunks...")
            docs = self.text_splitter.create_documents([text_content])
            if not docs:
                print(f"⚠️ Warning: No chunks were created for {document_name}.")

                return

            print(f"✅ Document '{document_name}' split into {len(docs)} semantic chunks")

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

            # Apply selected pre-embedding process
            processed_docs = self.apply_pre_embedding_process(docs, document_name)

            # PII Masking for all documents
            print(f"🔒 Applying PII masking to all {len(processed_docs)} documents...")
            for doc in processed_docs:
                masked = mask_text(doc.page_content)
                doc.page_content = masked


                # Store PII mapping with unique identifier
                doc_id = doc.metadata.get("chunk_id")
                if doc.metadata.get("content_type") == "hypothetical_prompt":
                    doc.metadata["chunk_id"] = f"{doc_id}_prompt_{doc.metadata.get('prompt_index')}"

            print(f"🗄️ Adding {len(processed_docs)} documents to vectorstore...")
            if vectorstore is None:
                vectorstore = FAISS.from_documents(processed_docs, self.embeddings)
            else:
                vectorstore.add_documents(processed_docs)


            print(f"📈 Total text processed: {len(text_content)} characters")
            print(f"📦 Total chunks in vectorstore: {vectorstore.index.ntotal}")

            # Update metrics
            vectorstore_total_chunks.observe(vectorstore.index.ntotal)


            # Save the vectorstore
            vectorstore.save_local(vectorstore_path)
            print(f"💾 Vector store saved to: {vectorstore_path}")

            # Log processing time
            processing_time = time.time() - start_time
            print(f"⏱️ Processing completed in {processing_time:.2f} seconds")

        except Exception as e:
            print(f"❌ Error in vector store processing: {str(e)}")
            raise e
