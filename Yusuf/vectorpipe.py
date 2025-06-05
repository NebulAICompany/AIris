import os
from langchain_experimental.text_splitter import SemanticChunker
from langchain_openai.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from pii_deneme import pii_mask
import json


class VectorStorePipeline:
    def __init__(self):
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        # Adjust semantic chunker parameters
        self.text_splitter = SemanticChunker(
            self.embeddings,
            breakpoint_threshold_type="percentile",
            breakpoint_threshold_amount=80,  # Lower threshold to create more chunks
        )

    def run(self, uploads_path: str, save_path: str):
        try:
<<<<<<< Updated upstream
            # Check if uploads directory is empty
            files = [f for f in os.listdir(uploads_path) if f.endswith((".txt"))]
=======
            files = [
                f for f in os.listdir(uploads_path) if f.endswith((".txt", ".pdf"))
            ]
>>>>>>> Stashed changes
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
                print(f"Loaded {len(vectorstore)} existing chunks")
            else:
                print("Creating new vector store...")
                vectorstore = None

            for file in files:
                file_path = os.path.join(uploads_path, file)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        text = f.read()
                        if not text.strip():
                            continue
                        total_text_length += len(text)
                        print(f"Read {len(text)} characters from {file}")
                except Exception as e:
                    print(f"Error reading file {file}: {str(e)}")
                    continue

                # Split the text into semantic chunks for this file
                docs = self.text_splitter.create_documents([text])
                if not docs:
                    print(f"Warning: No chunks were created for file {file}.")
                    continue

                print(f"✅ File '{file}' split into {len(docs)} semantic chunks")

                # PII Masking and metadata for each chunk
                for doc in docs:
                    masked, mapping = pii_mask(doc.page_content)
                    doc.page_content = masked
                    if not hasattr(doc, "metadata") or doc.metadata is None:
                        doc.metadata = {}
                    doc.metadata["chunk_id"] = f"chunk_{chunk_idx}"
                    doc.metadata["file_name"] = file
                    pii_chunk_maps[f"chunk_{chunk_idx}"] = mapping
                    chunk_idx += 1

                # Add documents to vectorstore
                if vectorstore is None:
                    vectorstore = FAISS.from_documents(docs, self.embeddings)
                else:
                    vectorstore.add_documents(docs)

                # Clean up only .txt files from uploads directory
                if file.endswith(".txt"):
                    os.remove(file_path)
                    print(f"✅ Deleted processed .txt file: {file}")

            if chunk_idx == 0:
                print("No valid text content found in files")
                return

            print(f"Total text length: {total_text_length} characters")
            print(f"\n✅ All files processed, total {chunk_idx} chunks created.")

            # Save the PII maps for all chunks
            pii_map_path = os.path.join(save_path, "pii_chunk_maps.json")
            with open(pii_map_path, "w", encoding="utf-8") as f:
                json.dump(pii_chunk_maps, f, ensure_ascii=False, indent=2)

            vectorstore.save_local(vectorstore_path)
            print(f"\n✅ Vector store updated and saved to '{vectorstore_path}'")

        except Exception as e:
            print(f"Error in vector store pipeline: {str(e)}")
            raise

<<<<<<< Updated upstream
=======
from langchain_community.vectorstores import FAISS
from openai import OpenAI
from langchain_openai.embeddings import OpenAIEmbeddings


class QueryPipeline:
    def __init__(self, query: str, vectorstore_path: str):
        self.query = query
        self.vectorstore_path = vectorstore_path

        if not os.environ.get("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY environment variable is not set")

    def find_similar_chunks(self):
        # Use the same embedding model as used for indexing
        vectorstore = FAISS.load_local(
            f"{self.vectorstore_path}",
            embeddings=OpenAIEmbeddings(model="text-embedding-3-small"),
            allow_dangerous_deserialization=True,
        )
        chunks_query_retriever = vectorstore.as_retriever(search_kwargs={"k": 2})
        similar_chunks = chunks_query_retriever.invoke(self.query)
        return similar_chunks

    def __generate_prompt(self):
        relevant_chunks = "\n".join(
            [chunk.page_content for chunk in self.find_similar_chunks()]
        )
        prompt = f"""Aşağıdaki verilen context'i KESİNLİKLE kullanarak, soruya **TÜM CEVABI MARKDOWN SYNTAXI İLE** formatla:
        - Başlıkları `##` ile oluştur
        - **Kalın** ve *italik* metin kullan
        - **Kalın** Yazdığın listelerden önce - işareti kullanma
        - Listeler için `.` veya `1.` gibi işaretler kullan
        - Context dışına çıkma!
       
        Context:
        {' '.join(relevant_chunks)}

        Soru: {self.query}

        Cevap:"""
        return prompt

    def generate_response(self):
        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

        response = client.chat.completions.create(
            model="gpt-4o-mini",  # GPT-4 modelini kullan (daha iyi Markdown desteği için)
            messages=[
                {
                    "role": "system",
                    "content": "TÜM CEVAPLARINI MARKDOWN İLE YAZ. Format: ## Başlık, **kalın**, *italik*, - liste.",
                },
                {"role": "user", "content": self.__generate_prompt()},
            ],
            temperature=0.3,
        )
        return response.choices[0].message.content

    # def save(self, similar_chunks: dict, save_path: str):
    #     if save_path is None:
    #         save_path = "query_results.txt"
    #     with open(save_path, "w", encoding="utf-8") as f:
    #         for chunk in similar_chunks:
    #             f.write(f"Chunk: {chunk['text']}\n")
    #             f.write(f"Similarity: {chunk['score']}\n\n")

    #     print(f"\n✅ Query complete! Saved to '{save_path}'")

>>>>>>> Stashed changes

import os

os.environ["OPENAI_API_KEY"] = (
    "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"  # Replace with your OpenAI key
)
# VectorStorePipeline().run(
#     uploads_path="D:/GitHub/vectorrag/Yusuf/uploads",
#     save_path="D:/GitHub/vectorrag/Yusuf/vectorstore",
# )
# print(QueryPipeline(
#     query="Proje özetini açıkla",
#     vectorstore_path="D:/GitHub/vectorrag/Yusuf/vectorstore",
# ).find_similar_chunks())
