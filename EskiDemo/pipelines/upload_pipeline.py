from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
import os
from pathlib import Path


class UploadPipeline:
    def __init__(
        self, file_path: str, azure_endpoint: str = None, azure_key: str = None
    ):
        self.file_path = file_path
        self.file_extension = Path(file_path).suffix.lower()

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
        # Determine file type and call appropriate processing method
        if self.file_extension in [".pdf", ".jpg", ".jpeg", ".png"]:
            return self._process_document()
        elif self.file_extension == ".pptx":
            return self._process_pptx()
        else:
            # Default to text processing
            return self._process_text()

    def _process_document(self):
        # Process PDF or image documents with Azure Document Intelligence
        try:
            with open(self.file_path, "rb") as f:
                poller = self.document_analysis_client.begin_analyze_document(
                    model_id="prebuilt-read", document=f
                )
            result = poller.result()

            # Convert result to structured text
            extracted_text = {"content": result.content, "pages": []}

            for page in result.pages:
                page_data = {
                    "page_number": page.page_number,
                    "blocks": [{"lines": []}],
                }

                for line in page.lines:
                    page_data["blocks"][0]["lines"].append(
                        {"words": [{"value": word} for word in line.content.split()]}
                    )

                extracted_text["pages"].append(page_data)

            return extracted_text

        except Exception as e:
            print(f"Error processing document: {str(e)}")
            return {
                "content": f"Error processing document: {str(e)}",
                "pages": [{"page_number": 1, "blocks": [{"lines": []}]}],
            }

    def _process_pptx(self):
        # Process PowerPoint presentations
        prs = Presentation(self.file_path)
        extracted_text = {"content": "", "pages": []}

        for i, slide in enumerate(prs.slides, 1):
            page_content = []
            page_data = {"page_number": i, "blocks": [{"lines": []}]}

            # Extract text from shapes
            for shape in slide.shapes:
                if hasattr(shape, "text") and shape.text.strip():
                    page_content.append(shape.text.strip())
                    words = shape.text.strip().split()
                    if words:
                        page_data["blocks"][0]["lines"].append(
                            {"words": [{"value": word} for word in words]}
                        )

            if page_content:
                slide_content = "\n".join(page_content)
                extracted_text["content"] += f"Slide {i}:\n{slide_content}\n\n"
                extracted_text["pages"].append(page_data)

        return extracted_text

    def _process_text(self):
        # Process text files (default fallback)
        try:
            with open(self.file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            lines = content.split("\n")
            extracted_text = {"content": content, "pages": []}

            page_data = {"page_number": 1, "blocks": [{"lines": []}]}

            for line in lines:
                if line.strip():
                    words = line.strip().split()
                    page_data["blocks"][0]["lines"].append(
                        {"words": [{"value": word} for word in words]}
                    )

            extracted_text["pages"].append(page_data)
            return extracted_text
        except Exception as e:
            print(f"Error reading text file {self.file_path}: {str(e)}")
            # Return minimal structure to prevent errors
            return {
                "content": "",
                "pages": [{"page_number": 1, "blocks": [{"lines": []}]}],
            }

    def save(self, extracted_text: dict, save_path: str = None):
        if save_path is None:
            # Use relative path if not specified
            from pathlib import Path
            base_dir = Path(__file__).resolve().parent.parent
            save_path = str(base_dir / "uploads")  # Updated path
            print(f"Default save path: {save_path}")

        if not os.path.exists(save_path):
            os.makedirs(save_path)

        # Get base filename without extension
        base_name = Path(self.file_path).stem
        output_file = os.path.join(save_path, f"{base_name}_ocr.txt")

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
