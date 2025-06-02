import os
from langchain_experimental.text_splitter import SemanticChunker
from langchain_openai.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS


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
            # Check if uploads directory is empty
            files = [f for f in os.listdir(uploads_path) if f.endswith((".txt"))]
            if not files:
                print("No text files found in uploads directory")
                return

            # Split the text into semantic chunks
            extracted_texts = []
            total_text_length = 0

            for file in files:
                file_path = os.path.join(uploads_path, file)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        text = f.read()
                        if text.strip():  # Check if text is not empty
                            extracted_texts.append(text)
                            total_text_length += len(text)
                            print(f"Read {len(text)} characters from {file}")
                except Exception as e:
                    print(f"Error reading file {file}: {str(e)}")

            if not extracted_texts:
                print("No valid text content found in files")
                return

            print(f"Total text length: {total_text_length} characters")

            # Create documents from texts
            docs = self.text_splitter.create_documents(extracted_texts)

            if not docs:
                print(
                    "Warning: No chunks were created. Text may be too short or uniform."
                )
                return

            print(f"\n✅ Text split into {len(docs)} semantic chunks")

            # Create or update vector store
            vectorstore_path = save_path
            if os.path.exists(os.path.join(vectorstore_path, "index.faiss")):
                print("Loading existing vector store...")
                vectorstore = FAISS.load_local(
                    vectorstore_path,
                    self.embeddings,
                    allow_dangerous_deserialization=True,
                )
                print(f"Loaded {len(vectorstore)} existing chunks")
                vectorstore.add_documents(docs)
            else:
                print("Creating new vector store...")
                os.makedirs(vectorstore_path, exist_ok=True)  # Updated path
                vectorstore = FAISS.from_documents(docs, self.embeddings)

            vectorstore.save_local(vectorstore_path)
            print(f"\n✅ Vector store updated and saved to '{vectorstore_path}'")

            # Clean up only .txt files from uploads directory
            for file in files:
                if file.endswith(".txt"):  # Only delete .txt files
                    os.remove(os.path.join(uploads_path, file))
                    print(f"✅ Deleted processed .txt file: {file}")

        except Exception as e:
            print(f"Error in vector store pipeline: {str(e)}")
            raise


import os

os.environ["OPENAI_API_KEY"] = (
    "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"  # Replace with your OpenAI key
)
# VectorStorePipeline().run(
#     uploads_path="D:/GitHub/vectorrag/Yusuf/uploads",
#     save_path="D:/GitHub/vectorrag/Yusuf/vectorstore",
# )
# print(QueryPipeline(
#     query="Resmi gazetenin madde 4'ünü açıkla",
#     vectorstore_path="D:/GitHub/vectorrag/Yusuf/vectorstore",
# ).find_similar_chunks())
