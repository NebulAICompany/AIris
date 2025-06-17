from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from aiiris_backend.orchestrator.query_orchestrator import run_orchestration
from aiiris_backend.monitoring.metrics import api_requests_total
from aiiris_backend.libs.logger import get_logger
import shutil
from pathlib import Path
import os
from datetime import datetime

router = APIRouter()
logger = get_logger(__name__)

# Simple request counter
request_counter = 0

class QueryRequest(BaseModel):
    query: str
    
class UploadRequest(BaseModel):
    file: str
    
@router.post("/query")
def handle_query(request: QueryRequest):
    """
    Kullanıcının gönderdiği sorguyu alır,
    orchestrator üzerinden işler ve LLM yanıtını döner.
    """
    global request_counter
    try:
        # Increment simple counter
        request_counter += 1
        
        query = request.query
        logger.info(f"Processing query: {query[:100]}...")  # Log first 100 chars
        
        answer = run_orchestration(query)
        api_requests_total.labels(status="success").inc()
        
        logger.info("Query processed successfully")
        return {"response": answer}
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        api_requests_total.labels(status="error").inc()
        raise e

@router.post("/upload")    
def handle_upload(file: UploadFile = File(...)):
    global request_counter
    try:
        # Increment simple counter
        request_counter += 1
        
        logger.info(f"Starting file upload: {file.filename} ({file.content_type})")
        
        # Ensure uploads directory exists (use absolute path)
        uploads_dir = Path(__file__).parent.parent / "uploads"
        uploads_dir.mkdir(parents=True, exist_ok=True)
        
        # Save uploaded file
        file_path = uploads_dir / file.filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        logger.info(f"File saved to: {file_path}")
        
        # Process the uploaded file
        from aiiris_backend.orchestrator.upload_orchestrator import process_file
        logger.info("Processing uploaded file...")
        result = process_file(str(file_path))
        
        logger.info(f"File processed successfully: {file.filename}")
        
        return {
            "filename": file.filename,
            "content_type": file.content_type,
            "status": "success",
            "message": "Dosya başarıyla yüklendi ve işlendi",
            "result": result
        }
    except Exception as e:
        error_message = str(e)
        logger.error(f"File upload error for {file.filename}: {error_message}")
        raise HTTPException(status_code=500, detail=f"Dosya yükleme hatası: {error_message}")
    
@router.get("/files")
def list_files():
    """
    Returns a list of files in the uploads directory with metadata.
    """
    try:
        #uploads_dir = Path("uploads")
        uploads_dir = Path(__file__).parent.parent / "uploads"
        if not uploads_dir.exists():
            return {"files": []}  # Return an empty list if the directory doesn't exist

        files = []
        for file in uploads_dir.iterdir():
            if file.is_file():
                files.append({
                    "name": file.name,
                    "size": file.stat().st_size,  # File size in bytes
                    "created_at": datetime.fromtimestamp(file.stat().st_ctime).isoformat(),  # Creation time in ISO 8601
                    "modified_at": datetime.fromtimestamp(file.stat().st_mtime).isoformat()  # Last modification time in ISO 8601
                })
        return {"files": files}
    except Exception as e:
        error_message = str(e)
        raise HTTPException(status_code=500, detail=f"Error listing files: {error_message}")

@router.get("/metrics")
def get_metrics():
    """
    Returns system metrics and analytics data.
    """
    try:
        # Get file count
        uploads_dir = Path(__file__).parent.parent / "uploads"
        file_count = len([f for f in uploads_dir.iterdir() if f.is_file()]) if uploads_dir.exists() else 0
        
        # Get vector store info
        vectorstore_dir = Path(__file__).parent.parent / "vectorstore"
        vectorstore_exists = vectorstore_dir.exists() and (vectorstore_dir / "index.faiss").exists()
        
        # Simple request counter - use module variable
        global request_counter
        total_requests = request_counter
        
        # Mock some metrics for demo
        import time
        current_time = time.time()
        
        return {
            "totalQueries": int(total_requests),
            "totalDocuments": file_count,
            "avgResponseTime": "1.2s",
            "systemHealth": "Healthy" if vectorstore_exists else "No Data",
            "vectorStoreStatus": "Active" if vectorstore_exists else "Empty",
            "lastUpdated": datetime.now().isoformat(),
            "recentActivity": [
                {
                    "title": "Document processed",
                    "time": "2 minutes ago",
                    "icon": "fas fa-file-upload"
                },
                {
                    "title": "Query answered",
                    "time": "5 minutes ago", 
                    "icon": "fas fa-comment"
                },
                {
                    "title": "System started",
                    "time": "1 hour ago",
                    "icon": "fas fa-power-off"
                }
            ]
        }
    except Exception as e:
        error_message = str(e)
        raise HTTPException(status_code=500, detail=f"Error fetching metrics: {error_message}")

@router.delete("/files/{filename}")
def delete_file(filename: str):
    """
    Delete a file from uploads directory and remove its chunks from vector store.
    """
    global request_counter
    try:
        logger.info(f"Starting deletion for file '{filename}'")
        
        # Increment simple counter
        request_counter += 1
        
        # Check if file exists in uploads directory
        uploads_dir = Path(__file__).parent.parent / "uploads"
        file_path = uploads_dir / filename
        
        logger.debug(f"Checking file existence: {file_path}")
        logger.debug(f"File exists: {file_path.exists()}")
        
        if not file_path.exists():
            logger.error(f"File not found: {filename}")
            raise HTTPException(status_code=404, detail=f"File '{filename}' not found")
        
        # Load vector store and PII mappings
        vectorstore_dir = Path(__file__).parent.parent / "vectorstore"
        
        logger.debug(f"Vector store directory: {vectorstore_dir}")
        logger.debug(f"Vector store exists: {vectorstore_dir.exists()}")
        logger.debug(f"FAISS index exists: {(vectorstore_dir / 'index.faiss').exists()}")
        
        if not vectorstore_dir.exists() or not (vectorstore_dir / "index.faiss").exists():
            # If no vector store exists, just delete the file
            logger.warning(f"No vector store found, deleting file only: {filename}")
            file_path.unlink()
            logger.info(f"File deleted successfully: {filename}")
            return {"message": f"File '{filename}' deleted successfully (no vector store found)"}
        
        # Load existing vector store
        from langchain_community.vectorstores import FAISS
        from langchain_openai.embeddings import OpenAIEmbeddings
        import json
        
        logger.info(f"Loading vector store from: {vectorstore_dir}")
        embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        vectorstore = FAISS.load_local(
            str(vectorstore_dir),
            embeddings,
            allow_dangerous_deserialization=True,
        )
        logger.info(f"Vector store loaded successfully")
        
        # Find all chunk IDs that belong to this file
        chunks_to_delete = []
        
        # Account for file processing transformations:
        # - PDF files are processed as "filename_txt.txt"
        # - DOCX files are converted to PDF then processed as "filename_txt.txt"
        # - Excel files might be processed differently
        base_filename = Path(filename).stem
        possible_processed_names = [
            filename,  # Original filename
            f"{base_filename}_txt.txt",  # PDF/DOCX processed format
            f"{base_filename}.txt",     # Alternative format
        ]
        
        # Get all documents and find ones with matching file_name
        # We need to iterate through the docstore to find matching documents
        for doc_id, document in vectorstore.docstore._dict.items():
            if hasattr(document, 'metadata'):
                doc_filename = document.metadata.get('file_name')
                if doc_filename in possible_processed_names:
                    chunks_to_delete.append(doc_id)
        
        print(f"🔍 Found {len(chunks_to_delete)} chunks to delete for file '{filename}' (checking: {possible_processed_names})")
        
        # Find chunk IDs to remove from PII maps BEFORE deleting from vector store
        chunks_to_remove_from_pii = []
        pii_map_path = vectorstore_dir / "pii_chunk_maps.json"
        print(f"📋 PII map path: {pii_map_path}")
        print(f"📋 PII map exists: {pii_map_path.exists()}")
        
        if pii_map_path.exists():
            with open(pii_map_path, "r", encoding="utf-8") as f:
                pii_maps = json.load(f)
            
            print(f"📋 Loaded PII maps with {len(pii_maps)} entries")
            
            # Find chunk IDs to remove from PII maps
            # We need to find chunks by their chunk_id metadata BEFORE deletion
            for doc_id, document in vectorstore.docstore._dict.items():
                if hasattr(document, 'metadata'):
                    doc_filename = document.metadata.get('file_name')
                    if doc_filename in possible_processed_names:
                        chunk_id = document.metadata.get('chunk_id')
                        if chunk_id and chunk_id in pii_maps:
                            chunks_to_remove_from_pii.append(chunk_id)
                            print(f"📋 Found PII entry to remove: {chunk_id}")
        
        # Delete chunks from vector store if any found
        if chunks_to_delete:
            print(f"🗑️ Deleting {len(chunks_to_delete)} chunks from vector store...")
            vectorstore.delete(ids=chunks_to_delete)
            
            # Save updated vector store
            print(f"💾 Saving updated vector store...")
            vectorstore.save_local(str(vectorstore_dir))
            print(f"✅ Deleted {len(chunks_to_delete)} chunks from vector store")
        else:
            print(f"⚠️ No chunks found to delete for file '{filename}'")
        
        # Update PII mappings - remove entries for deleted chunks
        if chunks_to_remove_from_pii and pii_map_path.exists():
            print(f"📋 Removing {len(chunks_to_remove_from_pii)} entries from PII mappings...")
            # Remove from PII maps
            for chunk_id in chunks_to_remove_from_pii:
                pii_maps.pop(chunk_id, None)
            
            # Save updated PII maps
            with open(pii_map_path, "w", encoding="utf-8") as f:
                json.dump(pii_maps, f, ensure_ascii=False, indent=2)
            
            print(f"✅ Removed {len(chunks_to_remove_from_pii)} entries from PII mappings")
        
        # Delete the actual file
        print(f"🗑️ Deleting physical file: {file_path}")
        file_path.unlink()
        print(f"✅ Physical file deleted successfully: {filename}")
        
        result = {
            "message": f"File '{filename}' deleted successfully",
            "chunks_deleted": len(chunks_to_delete),
            "pii_entries_removed": len(chunks_to_remove_from_pii),
            "file_path": str(file_path)
        }
        print(f"🎉 Deletion completed successfully: {result}")
        return result
        
    except HTTPException:
        print(f"❌ HTTP Exception during deletion: {filename}")
        raise
    except Exception as e:
        print(f"❌ Unexpected error deleting file '{filename}': {str(e)}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error deleting file: {str(e)}")
    
if __name__ == "__main__":
    file_path = "C:/Users/ASUS/Desktop/Coding/Python/vectorrag/Esra/pdf_file.pdf" # Change this to your file path
    with open(file_path, "rb") as file:
        file = UploadFile(file)
        handle_upload(file)
