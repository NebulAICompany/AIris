import os
import sys
from pathlib import Path
import json
from langchain_core.documents import Document

# Add the project root to system path to allow imports
sys.path.append(str(Path(__file__).resolve().parent.parent.parent.parent))

# Import from upload.py and buraya.py
from upload import UploadPipeline
import buraya

# Vector store path
VECTOR_STORE_PATH = "aiiris_backend/retrieval/vectorstore"

def process_file(file_path: str) -> dict:
    """
    Process an uploaded file synchronously.
    
    Args:
        file_path: Path to the uploaded file
        
    Returns:
        Dictionary with processing results
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Uploaded file not found: {file_path}")

    _, ext = os.path.splitext(file_path)
    
    if ext.lower() != '.pdf':
        raise ValueError(f"Unsupported file format: {ext}")

    try:
        # Step 1: Create UploadPipeline
        pipeline = UploadPipeline(pdf_path=file_path)
        
        # Step 2: Process PDF
        extracted_data = pipeline.z()
        
        # Step 3: Save extracted data to JSON
        json_path = pipeline.save_as_json(extracted_data)
        
        # Step 4: Convert extracted data to documents
        documents = []
        for item in extracted_data:
            if 'content' in item and item.get('type') == 'text':
                doc = Document(
                    page_content=item['content'],
                    metadata={
                        'source_file': item.get('source_file', file_path),
                        'page_number': item.get('page_number'),
                        'type': 'text'
                    }
                )
                documents.append(doc)
            elif 'content' in item and item.get('type') == 'table':
                table_content = json.dumps(item['content'])
                doc = Document(
                    page_content=table_content,
                    metadata={
                        'source_file': item.get('source_file', file_path),
                        'page_number': item.get('page_number'),
                        'type': 'table'
                    }
                )
                documents.append(doc)
        
        # Step 5: Update vector store
        if hasattr(buraya, 'update_vector_store'):
            result = buraya.update_vector_store(documents, VECTOR_STORE_PATH)
        else:
            from langchain_community.vectorstores import FAISS
            embeddings = buraya.OpenAIEmbeddings() if hasattr(buraya, 'OpenAIEmbeddings') else None
            os.makedirs(VECTOR_STORE_PATH, exist_ok=True)
            if os.path.exists(os.path.join(VECTOR_STORE_PATH, "index.faiss")):
                vectorstore = FAISS.load_local(folder_path=VECTOR_STORE_PATH, embeddings=embeddings)
                vectorstore.add_documents(documents)
            else:
                vectorstore = FAISS.from_documents(documents=documents, embedding=embeddings)
            vectorstore.save_local(folder_path=VECTOR_STORE_PATH)
            result = {"vector_store_updated": True, "documents_added": len(documents)}
        
        return {
            "processed": True,
            "document_count": len(documents),
            "json_path": str(json_path),
            "extraction_type": "pdf",
            "vector_store_result": result,
            "document_elements": {
                "text": sum(1 for x in extracted_data if x.get('type') == 'text'),
                "tables": sum(1 for x in extracted_data if x.get('type') == 'table'),
                "images": sum(1 for x in extracted_data if x.get('type') == 'image')
            }
        }
    except Exception as e:
        print(f"Error processing file: {str(e)}")
        raise e