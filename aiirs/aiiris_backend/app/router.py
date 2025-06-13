from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from aiiris_backend.orchestrator.query_orchestrator import run_orchestration
from aiiris_backend.monitoring.metrics import api_requests_total
import shutil
from pathlib import Path
import os
from datetime import datetime

router = APIRouter()

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
    try:
        query = request.query
        answer = run_orchestration(query)
        api_requests_total.labels(status="success").inc()
        return {"response": answer}
    except Exception as e:
        api_requests_total.labels(status="error").inc()
        raise e

@router.post("/upload")    
def handle_upload(file: UploadFile = File(...)):
    try:
        # Ensure uploads directory exists (use absolute path)
        uploads_dir = Path(__file__).parent.parent / "uploads"
        uploads_dir.mkdir(parents=True, exist_ok=True)
        
        # Save uploaded file
        file_path = uploads_dir / file.filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Process the uploaded file
        from aiiris_backend.orchestrator.upload_orchestrator import process_file
        result = process_file(str(file_path))
        
        return {
            "filename": file.filename,
            "content_type": file.content_type,
            "status": "success",
            "message": "Dosya başarıyla yüklendi ve işlendi",
            "result": result
        }
    except Exception as e:
        error_message = str(e)
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
    
if __name__ == "__main__":
    file_path = "C:/Users/ASUS/Desktop/Coding/Python/vectorrag/Esra/pdf_file.pdf" # Change this to your file path
    with open(file_path, "rb") as file:
        file = UploadFile(file)
        handle_upload(file)
