import os
import sys
from pathlib import Path
import json
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings

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

        pipeline.run()
        save_dir = Path(__file__).resolve().parent / "uploads"
        # Step 2: Create or update vector store
        buraya.VectorStorePipeline(
        ).run(uploads_path=save_dir, save_path=VECTOR_STORE_PATH)

        return {
            "status": "success",
            "message": "File processed successfully",
            "vector_store_path": VECTOR_STORE_PATH
        }
    except Exception as e:
        print(f"Error processing file: {str(e)}")
        raise e