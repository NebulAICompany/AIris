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

    def save(self, extracted_text: dict, save_path: str):
        if save_path is None:
            save_path = self.pdf_path.replace(".pdf", "_ocr.txt")
        elif not save_path.endswith(".pdf"):
            if not os.path.exists(save_path):
                os.mkdir(save_path)
            save_path = os.path.join(save_path, self.pdf_path.replace(".pdf", "_ocr.txt"))
        with open(save_path, "w", encoding="utf-8") as f:
            for page_num, page in enumerate(extracted_text["pages"], start=1):
                f.write(f"\n--- Page {page_num} ---\n")
                for block in page["blocks"]:
                    for line in block["lines"]:
                        f.write(" ".join(word["value"] for word in line["words"]) + "\n")

        print(f"\n✅ Text extraction complete! Saved to '{save_path}'")



from langchain_experimental.text_splitter import SemanticChunker
from langchain_openai.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS

class VectorStorePipeline:
    def __init__(self):
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
        self.text_splitter = SemanticChunker(self.embeddings, breakpoint_threshold_type='percentile', breakpoint_threshold_amount=90) # chose which embeddings and breakpoint type and threshold to use)
        
    def run(self, uploads_path: str, save_path: str):
        # Split the text into semantic chunks
        extracted_texts = []
        print(os.getcwd())
        for _, _, files in os.walk(uploads_path):
            for file in files:
                with open(os.path.join(uploads_path, file), "r", encoding="utf-8") as f:
                    extracted_text = f.read()
                    extracted_texts.append(extracted_text)
        docs = self.text_splitter.create_documents(extracted_texts)
        print(f"\n✅ Text split into {len(docs)} semantic chunks")
        vectorstore_path = f"{save_path}"
        if os.path.exists(vectorstore_path):
            # Load existing vectorstore
            vectorstore = FAISS.load_local(vectorstore_path, self.embeddings,allow_dangerous_deserialization=True)
            print(f"\n✅ Loaded existing vector store from '{vectorstore_path}'")
            # Add new documents to the vectorstore
            vectorstore.add_documents(docs)
        else:
            # Create new vectorstore
            vectorstore = FAISS.from_documents(docs, self.embeddings)
            print(f"\n✅ Created new vector store")
            os.mkdir(save_path)
        vectorstore.save_local(vectorstore_path)
        print(f"\n✅ Vector store updated and saved to '{vectorstore_path}'")

        # Delete the files in the uploads_path
        for _, _, files in os.walk(uploads_path):
            for file in files:
                file_path = os.path.join(uploads_path, file)
                os.remove(file_path)
                print(f"\n✅ Deleted file '{file_path}'")
        # chunks_query_retriever = vectorstore.as_retriever(search_kwargs={"k": 2})
        # return chunks_query_retriever



upload_pipeline = UploadPipeline(pdf_path="20250114-pages-14.pdf")
upload_pipeline.save(upload_pipeline.run(), "uploads")

os.environ["OPENAI_API_KEY"] = "***REMOVED***"  # Replace with your OpenAI key

vector_store_pipeline = VectorStorePipeline()
vector_store_pipeline.run("uploads", "vectorstore")


