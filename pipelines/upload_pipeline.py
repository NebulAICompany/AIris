from doctr.io import DocumentFile
from doctr.models import ocr_predictor
import os


class UploadPipeline:
    def __init__(self, pdf_path: str, reco_arch: str = "parseq"):
        self.pdf_path = pdf_path
        self.reco_arch = reco_arch

    def run(self):
        # Load the PDF file
        doc = DocumentFile.from_pdf(self.pdf_path)

        # Load the OCR model (pretrained)
        model = ocr_predictor(pretrained=True, reco_arch=self.reco_arch)

        # Perform OCR
        result = model(doc)

        # Convert result to structured text
        extracted_text = result.export()

        return extracted_text

    def save(self, extracted_text: dict, save_path: str = None):
        if save_path is None:
            save_path = "C:/Users/ASUS/Desktop/Coding/Python/vectorrag/uploads"
        if not os.path.exists(save_path):
            os.makedirs(save_path)
        save_path = os.path.join(
            save_path, os.path.basename(self.pdf_path).replace(".pdf", "_ocr.txt")
        )

        with open(save_path, "w", encoding="utf-8") as f:
            for page_num, page in enumerate(extracted_text["pages"], start=1):
                f.write(f"\n--- Page {page_num} ---\n")
                for block in page["blocks"]:
                    for line in block["lines"]:
                        f.write(
                            " ".join(word["value"] for word in line["words"]) + "\n"
                        )

        print(f"\n✅ Text extraction complete! Saved to '{save_path}'")


from langchain_experimental.text_splitter import SemanticChunker
from langchain_openai.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS


# ...existing code...


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

            # Clean up uploads directory
            for file in files:
                os.remove(os.path.join(uploads_path, file))
                print(f"✅ Deleted processed file: {file}")

        except Exception as e:
            print(f"Error in vector store pipeline: {str(e)}")
            raise


# ...existing code...
