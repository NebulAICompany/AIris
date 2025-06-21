import os
from langchain_experimental.text_splitter import SemanticChunker
from langchain_openai.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from .pii_deneme import pii_mask
import json
from openai import OpenAI
from pathlib import Path
from typing import List, Dict
import time
from aiiris_backend.monitoring.metrics import (
    hype_indexing_duration_seconds,
    hype_hypothetical_content_generated,
    hype_enhanced_documents_indexed,
    vectorstore_total_chunks,
)

# Get OpenAI client
PROJECT_ROOT = Path(__file__).parent.parent.parent
import dotenv

env_path = PROJECT_ROOT / ".env"
dotenv.load_dotenv(env_path)


class HyPEVectorStorePipeline:
    """
    HyPE-Enhanced Vector Store Pipeline
    Generates hypothetical prompts/queries for each document chunk during indexing
    """

    def __init__(self):
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        # Adjust semantic chunker parameters
        self.text_splitter = SemanticChunker(
            self.embeddings,
            breakpoint_threshold_type="percentile",
            breakpoint_threshold_amount=80,  # Lower threshold to create more chunks
        )
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def generate_hypothetical_prompts(
        self, original_chunk: str, chunk_metadata: Dict
    ) -> List[str]:
        """
        Generate hypothetical prompts/queries that users might ask to find this document chunk
        """
        try:
            # Determine content type from metadata for better prompts
            file_name = chunk_metadata.get("file_name", "")
            file_type = "genel"

            if any(
                keyword in file_name.lower()
                for keyword in ["bilanco", "balance", "financial"]
            ):
                file_type = "finansal"
            elif any(keyword in file_name.lower() for keyword in ["budget", "bütçe"]):
                file_type = "bütçe"
            elif any(
                keyword in file_name.lower()
                for keyword in ["ikt", "ekonomik", "economic"]
            ):
                file_type = "ekonomik"
            elif any(
                keyword in file_name.lower()
                for keyword in ["tufe", "enflasyon", "inflation"]
            ):
                file_type = "istatistik"

            # Create context-aware system prompt for generating hypothetical queries
            system_prompt = f"""Sen bir uzman soru üretme asistanısın. Verilen belge parçası için, kullanıcıların bu bilgiyi bulmak üzere sorabileceği hipotetik sorular/sorgular üret.

Belge türü: {file_type}

Bu hipotetik sorular:
1. Belgede bulunan bilgileri arayan farklı türde sorular olmalı
2. Farklı detay seviyelerinde sorular içermeli (genel, spesifik)
3. Farklı bakış açılarından sorulan sorular olmalı
4. Türkçe iş dünyası terminolojisini kullanmalı
5. Kullanıcıların bu belgeyi bulması için sorabileceği gerçekçi sorular olmalı

Her soruyu ||| ile ayır. Sadece soruları ver, açıklama yapma."""

            user_prompt = f"""Belge içeriği:
{original_chunk}

Bu belge içeriği için kullanıcıların sorabileceği 3 farklı hipotetik soru/sorgu üret:"""

            response = self.client.chat.completions.create(
                model="gpt-4.1",
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

            # Limit to 5 hypothetical prompts per chunk
            hypothetical_prompts = hypothetical_prompts[:5]

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

    def run(self, uploads_path: str, save_path: str):
        start_time = time.time()

        try:
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

                # Clean up only .txt files from uploads directory
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

            vectorstore.save_local(vectorstore_path)
            print(
                f"✅ HyPE (Hypothetical Prompt Embeddings) enhanced vector store saved to '{vectorstore_path}'"
            )
            print(f"🎉 HyPE processing completed successfully!")

        except Exception as e:
            print(f"❌ Error in HyPE vector store pipeline: {str(e)}")
            raise
        finally:
            # Record indexing duration
            duration = time.time() - start_time
            hype_indexing_duration_seconds.observe(duration)
            print(f"⏱️ HyPE indexing completed in {duration:.2f} seconds")


# Keep the original VectorStorePipeline for backward compatibility
class VectorStorePipeline(HyPEVectorStorePipeline):
    """
    Original VectorStorePipeline - now inherits from HyPE version
    """

    pass


# Remove hardcoded API key - now uses environment variable
# VectorStorePipeline().run(
#     uploads_path="D:/GitHub/vectorrag/Yusuf/uploads",
#     save_path="D:/GitHub/vectorrag/Yusuf/vectorstore",
# )
# print(QueryPipeline(
#     query="Proje özetini açıkla",
#     query="Proje özetini açıkla",
#     vectorstore_path="D:/GitHub/vectorrag/Yusuf/vectorstore",
# ).find_similar_chunks())
