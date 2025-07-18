import os
from langchain_experimental.text_splitter import SemanticChunker
from langchain_openai.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from .pii_deneme import pii_mask
import json
from openai import OpenAI
from pathlib import Path
from typing import List, Dict, Optional, Literal
import time
import asyncio
from enum import Enum
from aiiris_backend.monitoring.metrics import (
    hype_indexing_duration_seconds,
    hype_hypothetical_content_generated,
    hype_enhanced_documents_indexed,
    vectorstore_total_chunks,
)
from aiiris_backend.retrieval.autocontext import apply_autocontext

# Get OpenAI client
PROJECT_ROOT = Path(__file__).parent.parent.parent
import dotenv

env_path = PROJECT_ROOT / ".env"
dotenv.load_dotenv(env_path)


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

    def __init__(self, pre_embedding_process: PreEmbeddingProcess = PreEmbeddingProcess.NONE):
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        # Adjust semantic chunker parameters
        self.text_splitter = SemanticChunker(
            self.embeddings,
            breakpoint_threshold_type="percentile",
            breakpoint_threshold_amount=80,  # Lower threshold to create more chunks
        )
        self.pre_embedding_process = pre_embedding_process
        
        # Initialize OpenAI client if HyPE is enabled
        if self.pre_embedding_process == PreEmbeddingProcess.HYPE:
            self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def generate_hypothetical_prompts(
        self, original_chunk: str, chunk_metadata: Dict
    ) -> List[str]:
        """
        Generate hypothetical prompts/queries that users might ask to find this document chunk
        """
        try:
            # Determine content type from metadata for better prompts
            file_name = chunk_metadata.get("file_name", "document")
            content_type = "general"
            
            if any(keyword in file_name.lower() for keyword in ["financial", "budget", "report"]):
                content_type = "financial"
            elif any(keyword in file_name.lower() for keyword in ["technical", "manual", "guide"]):
                content_type = "technical"
            elif any(keyword in file_name.lower() for keyword in ["legal", "contract", "agreement"]):
                content_type = "legal"

            # Create prompts based on content type
            if content_type == "financial":
                system_prompt = """Sen bir finansal belge analisti ve soru üretim uzmanısın. 
                Verilen belge parçası için kullanıcıların sorabileceği hipotetik sorular üret.
                Sorular finansal terimler, sayısal veriler ve analiz odaklı olmalı."""
            elif content_type == "technical":
                system_prompt = """Sen bir teknik belge analisti ve soru üretim uzmanısın.
                Verilen belge parçası için kullanıcıların sorabileceği hipotetik sorular üret.
                Sorular teknik prosedürler, özellikler ve nasıl yapılır odaklı olmalı."""
            elif content_type == "legal":
                system_prompt = """Sen bir hukuki belge analisti ve soru üretim uzmanısın.
                Verilen belge parçası için kullanıcıların sorabileceği hipotetik sorular üret.
                Sorular yasal şartlar, yükümlülükler ve haklar odaklı olmalı."""
            else:
                system_prompt = """Sen bir belge analisti ve soru üretim uzmanısın.
                Verilen belge parçası için kullanıcıların sorabileceği hipotetik sorular üret.
                Sorular belgenin içeriği ve konusu hakkında olmalı."""

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

            # Split by separator and clean
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

        except Exception as e:
            print(f"❌ Error generating hypothetical prompts: {e}")
            return []

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

    def apply_pre_embedding_process(self, docs: List[Document], file_name: str) -> List[Document]:
        """
        Apply the selected pre-embedding process to the documents
        """
        if self.pre_embedding_process == PreEmbeddingProcess.NONE:
            print(f"📝 No pre-embedding processing applied to {file_name}")
            return docs
        
        elif self.pre_embedding_process == PreEmbeddingProcess.CCH:
            print(f"🔗 Applying Contextual Chunk Headers (AutoContext) to {file_name}...")
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
                                    lambda: asyncio.run(apply_autocontext(docs, file_name=file_name, enabled=True))
                                )
                                return future.result()
                        else:
                            return loop.run_until_complete(
                                apply_autocontext(docs, file_name=file_name, enabled=True)
                            )
                    except RuntimeError:
                        # No event loop exists, create a new one
                        return asyncio.run(apply_autocontext(docs, file_name=file_name, enabled=True))
                
                processed_docs = run_autocontext()
                print(f"✅ Contextual Chunk Headers applied to {len(processed_docs)} chunks")
                return processed_docs
                
            except Exception as e:
                print(f"⚠️ AutoContext processing failed for {file_name}: {e}")
                print("   Continuing with original chunks...")
                return docs
        
        elif self.pre_embedding_process == PreEmbeddingProcess.HYPE:
            print(f"❓ Applying HyPE (Hypothetical Prompt Embeddings) to {file_name}...")
            try:
                enhanced_docs = self.create_enhanced_documents(docs, file_name)
                original_count = len(docs)
                enhanced_count = len(enhanced_docs)
                prompt_count = enhanced_count - original_count
                
                print(f"✅ HyPE applied: {original_count} original + {prompt_count} prompt documents = {enhanced_count} total")
                return enhanced_docs
                
            except Exception as e:
                print(f"⚠️ HyPE processing failed for {file_name}: {e}")
                print("   Continuing with original chunks...")
                return docs
        
        else:
            print(f"⚠️ Unknown pre-embedding process: {self.pre_embedding_process}")
            return docs

    def run(self, uploads_path: str, save_path: str, specific_file: str = None):
        start_time = time.time()

        try:
            if specific_file:
                # Process only the specific file if provided
                if os.path.exists(
                    os.path.join(uploads_path, specific_file)
                ) and specific_file.endswith((".txt")):
                    files = [specific_file]
                    print(f"Processing specific file: {specific_file}")
                else:
                    print(f"Specific file {specific_file} not found or not a .txt file")
                    return
            else:
                # Original behavior: process all .txt files
                files = [f for f in os.listdir(uploads_path) if f.endswith((".txt"))]
                if not files:
                    print("No text files found in uploads directory")
                    return

            total_text_length = 0
            chunk_idx = 0
            pii_chunk_maps = {}

            # Ensure save_path exists before saving the PII maps or vectorstore
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

            print(f"🚀 Starting vector store processing with pre-embedding process: {self.pre_embedding_process.value}")

            for file in files:
                file_path = os.path.join(uploads_path, file)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        text = f.read()
                        if not text.strip():
                            continue
                        total_text_length += len(text)
                        print(f"📖 Read {len(text)} characters from {file}")
                except Exception as e:
                    print(f"❌ Error reading file {file}: {str(e)}")
                    continue

                # Split the text into semantic chunks for this file
                print(f"✂️ Splitting {file} into semantic chunks...")
                docs = self.text_splitter.create_documents([text])
                if not docs:
                    print(f"⚠️ Warning: No chunks were created for file {file}.")
                    continue

                print(f"✅ File '{file}' split into {len(docs)} semantic chunks")

                # Add basic metadata to original chunks
                for doc in docs:
                    if not hasattr(doc, "metadata") or doc.metadata is None:
                        doc.metadata = {}
                    doc.metadata["chunk_id"] = f"chunk_{chunk_idx}"
                    doc.metadata["file_name"] = file
                    doc.metadata["content_type"] = "original"
                    chunk_idx += 1

                # Apply selected pre-embedding process
                processed_docs = self.apply_pre_embedding_process(docs, file)

                # PII Masking for all documents
                print(f"🔒 Applying PII masking to all {len(processed_docs)} documents...")
                for doc in processed_docs:
                    masked, mapping = pii_mask(doc.page_content)
                    doc.page_content = masked

                    # Store PII mapping with unique identifier
                    doc_id = doc.metadata.get("chunk_id")
                    if doc.metadata.get("content_type") == "hypothetical_prompt":
                        doc_id = f"{doc_id}_prompt_{doc.metadata.get('prompt_index')}"
                        doc.metadata["chunk_id"] = doc_id

                    pii_chunk_maps[doc_id] = mapping

                # Add documents to vectorstore
                print(f"🗄️ Adding {len(processed_docs)} documents to vectorstore...")
                if vectorstore is None:
                    vectorstore = FAISS.from_documents(processed_docs, self.embeddings)
                else:
                    vectorstore.add_documents(processed_docs)

                # Clean up processed .txt file
                if file.endswith(".txt"):
                    os.remove(file_path)
                    print(f"🗑️ Deleted processed .txt file: {file}")

            if chunk_idx == 0:
                print("❌ No valid text content found in files")
                return

            print(f"📈 Total text processed: {total_text_length} characters")
            print(f"📦 Total chunks in vectorstore: {vectorstore.index.ntotal}")

            # Update metrics
            vectorstore_total_chunks.observe(vectorstore.index.ntotal)

            # Save the PII maps for all chunks
            pii_map_path = os.path.join(save_path, "pii_chunk_maps.json")
            with open(pii_map_path, "w", encoding="utf-8") as f:
                json.dump(pii_chunk_maps, f, ensure_ascii=False, indent=2)

            # Save the vectorstore
            vectorstore.save_local(vectorstore_path)
            print(f"💾 Vector store saved to: {vectorstore_path}")

            # Log processing time
            processing_time = time.time() - start_time
            print(f"⏱️ Processing completed in {processing_time:.2f} seconds")

        except Exception as e:
            print(f"❌ Error in vector store processing: {str(e)}")
            raise e


# Legacy class for backward compatibility
class HyPEVectorStorePipeline(VectorStorePipeline):
    """
    Legacy HyPE-Enhanced Vector Store Pipeline
    Maintained for backward compatibility - now uses the new VectorStorePipeline with HyPE process
    """

    def __init__(self, autocontext_enabled: bool = False):
        # Convert legacy parameters to new system
        if autocontext_enabled:
            process = PreEmbeddingProcess.CCH
        else:
            process = PreEmbeddingProcess.HYPE
        
        super().__init__(pre_embedding_process=process)
        
        # Keep legacy attribute for compatibility
        self.autocontext_enabled = autocontext_enabled
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def run(self, uploads_path: str, save_path: str, specific_file: str = None):
        start_time = time.time()

        try:
            if specific_file:
                # Process only the specific file if provided
                if os.path.exists(
                    os.path.join(uploads_path, specific_file)
                ) and specific_file.endswith((".txt")):
                    files = [specific_file]
                    print(f"Processing specific file: {specific_file}")
                else:
                    print(f"Specific file {specific_file} not found or not a .txt file")
                    return
            else:
                # Original behavior: process all .txt files
                files = [f for f in os.listdir(uploads_path) if f.endswith((".txt"))]
                if not files:
                    print("No text files found in uploads directory")
                    return

            total_text_length = 0
            chunk_idx = 0
            pii_chunk_maps = {}

            # Ensure save_path exists before saving the PII maps or vectorstore
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

            print("🚀 Starting HyPE (Hypothetical Prompt Embeddings) processing...")

            for file in files:
                file_path = os.path.join(uploads_path, file)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        text = f.read()
                        if not text.strip():
                            continue
                        total_text_length += len(text)
                        print(f"📖 Read {len(text)} characters from {file}")
                except Exception as e:
                    print(f"❌ Error reading file {file}: {str(e)}")
                    continue

                # Split the text into semantic chunks for this file
                print(f"✂️ Splitting {file} into semantic chunks...")
                docs = self.text_splitter.create_documents([text])
                if not docs:
                    print(f"⚠️ Warning: No chunks were created for file {file}.")
                    continue

                print(f"✅ File '{file}' split into {len(docs)} semantic chunks")

                # Add basic metadata to original chunks
                for doc in docs:
                    if not hasattr(doc, "metadata") or doc.metadata is None:
                        doc.metadata = {}
                    doc.metadata["chunk_id"] = f"chunk_{chunk_idx}"
                    doc.metadata["file_name"] = file
                    doc.metadata["content_type"] = "original"
                    chunk_idx += 1

                # Apply AutoContext processing if enabled (legacy behavior)
                if self.autocontext_enabled:
                    print(f"🔗 Applying AutoContext to {file}...")
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
                                            lambda: asyncio.run(apply_autocontext(docs, file_name=file, enabled=True))
                                        )
                                        return future.result()
                                else:
                                    return loop.run_until_complete(
                                        apply_autocontext(docs, file_name=file, enabled=True)
                                    )
                            except RuntimeError:
                                # No event loop exists, create a new one
                                return asyncio.run(apply_autocontext(docs, file_name=file, enabled=True))
                        
                        docs = run_autocontext()
                        print(f"✅ AutoContext applied to {len(docs)} chunks")
                    except Exception as e:
                        print(f"⚠️ AutoContext processing failed for {file}: {e}")
                        # Continue with original docs if AutoContext fails

                # Generate hypothetical prompts and create enhanced document set
                print(f"❓ Generating hypothetical prompts for {file}...")
                enhanced_docs = self.create_enhanced_documents(docs, file)

                original_count = len(docs)
                enhanced_count = len(enhanced_docs)
                prompt_count = enhanced_count - original_count

                print(
                    f"📊 Enhanced document set: {original_count} original + {prompt_count} prompt documents = {enhanced_count} total"
                )

                # PII Masking for all documents (original + prompt documents)
                print(f"🔒 Applying PII masking to all {enhanced_count} documents...")
                for doc in enhanced_docs:
                    masked, mapping = pii_mask(doc.page_content)
                    doc.page_content = masked

                    # Store PII mapping with unique identifier
                    doc_id = doc.metadata.get("chunk_id")
                    if doc.metadata.get("content_type") == "hypothetical_prompt":
                        doc_id = f"{doc_id}_prompt_{doc.metadata.get('prompt_index')}"
                        doc.metadata["chunk_id"] = doc_id

                    pii_chunk_maps[doc_id] = mapping

                # Add documents to vectorstore
                print(f"🗄️ Adding {len(enhanced_docs)} documents to vectorstore...")
                if vectorstore is None:
                    vectorstore = FAISS.from_documents(enhanced_docs, self.embeddings)
                else:
                    vectorstore.add_documents(enhanced_docs)

                # Clean up processed .txt file
                if file.endswith(".txt"):
                    os.remove(file_path)
                    print(f"🗑️ Deleted processed .txt file: {file}")

            if chunk_idx == 0:
                print("❌ No valid text content found in files")
                return

            print(f"📈 Total text processed: {total_text_length} characters")
            print(f"📦 Total chunks in vectorstore: {vectorstore.index.ntotal}")

            # Update metrics
            vectorstore_total_chunks.observe(vectorstore.index.ntotal)

            # Save the PII maps for all chunks
            pii_map_path = os.path.join(save_path, "pii_chunk_maps.json")
            with open(pii_map_path, "w", encoding="utf-8") as f:
                json.dump(pii_chunk_maps, f, ensure_ascii=False, indent=2)

            # Save the vectorstore
            vectorstore.save_local(vectorstore_path)
            print(f"💾 Vector store saved to: {vectorstore_path}")

            # Log processing time
            processing_time = time.time() - start_time
            print(f"⏱️ Processing completed in {processing_time:.2f} seconds")

        except Exception as e:
            print(f"❌ Error in vector store processing: {str(e)}")
            raise e
