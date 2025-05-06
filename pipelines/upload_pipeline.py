from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
import os
from pathlib import Path


class UploadPipeline:
    def __init__(
        self, pdf_path: str, azure_endpoint: str = None, azure_key: str = None
    ):
        self.pdf_path = pdf_path

        # Get Azure credentials from environment variables if not provided
        self.azure_endpoint = azure_endpoint or os.environ.get(
            "AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"
        )
        self.azure_key = azure_key or os.environ.get("AZURE_DOCUMENT_INTELLIGENCE_KEY")

        if not self.azure_endpoint or not self.azure_key:
            raise ValueError(
                "Azure Document Intelligence credentials not provided. "
                "Set AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT and AZURE_DOCUMENT_INTELLIGENCE_KEY "
                "environment variables or pass them as parameters."
            )

        self.document_analysis_client = DocumentAnalysisClient(
            endpoint=self.azure_endpoint, credential=AzureKeyCredential(self.azure_key)
        )

    def run(self):
        # Load and process the PDF file with Azure Document Intelligence
        with open(self.pdf_path, "rb") as f:
            poller = self.document_analysis_client.begin_analyze_document(
                "prebuilt-read", document=f )
        result = poller.result()

        # Convert result to structured text
        extracted_text = {"content": result.content, "pages": []}

        for page in result.pages:
            page_data = {
                "page_number": page.page_number,
                "blocks": [
                    {"lines": []}
                ],  # Maintaining structure similar to original format
            }

            for line in page.lines:
                page_data["blocks"][0]["lines"].append(
                    {"words": [{"value": word} for word in line.content.split()]}
                )

            extracted_text["pages"].append(page_data)

        return extracted_text

    def save(self, extracted_text: dict, save_path: str = None):
        if save_path is None:
            # Use relative path if not specified
            base_dir = Path(__file__).resolve().parent.parent
            save_path = str(base_dir / "uploads")

        if not os.path.exists(save_path):
            os.makedirs(save_path)

        output_file = os.path.join(
            save_path, os.path.basename(self.pdf_path).replace(".pdf", "_ocr.txt")
        )

        with open(output_file, "w", encoding="utf-8") as f:
            for page_num, page in enumerate(extracted_text["pages"], start=1):
                f.write(f"\n--- Page {page_num} ---\n")
                for block in page["blocks"]:
                    for line in block["lines"]:
                        f.write(
                            " ".join(word["value"] for word in line["words"]) + "\n"
                        )

        print(f"\n✅ Text extraction complete! Saved to '{output_file}'")


from langchain_experimental.text_splitter import SemanticChunker
from langchain_openai.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS


class VectorStorePipeline:
    def __init__(self):
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
        # Adjust semantic chunker parameters
        self.text_splitter = SemanticChunker(
            self.embeddings,
            breakpoint_threshold_type="percentile",
            breakpoint_threshold_amount=80,  # Lower threshold to create more chunks
        )

    def run(self, uploads_path: str, save_path: str):
        try:
            # Check if uploads directory is empty
            files = [
                f for f in os.listdir(uploads_path) if f.endswith((".txt", ".pdf"))
            ]
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
                vectorstore.add_documents(docs)
            else:
                print("Creating new vector store...")
                os.makedirs(vectorstore_path, exist_ok=True)
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
