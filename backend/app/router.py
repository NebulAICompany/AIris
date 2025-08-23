from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel
from backend.pipeline.query import run_orchestration
from backend.core.chat import chat_history_manager
from backend.monitoring.metrics import api_requests_total
from backend.shared.logger import get_logger
from backend.shared.constants import (
    UPLOADS_PATH,
    VECTORSTORE_PATH_STR,
    VERIFICATION_UPLOADS_PATH,
    MASKED_MAP_JSON_PATH,
    CREATED_DOCUMENTS_PATH,
    DEFAULT_SEARCH_METHOD,
)
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Optional
from backend.utils.news import fetch_and_parse_news
from qdrant_client import models

logger = get_logger("ROUTER")
router = APIRouter()
# Simple request counter
request_counter = 0


class QueryRequest(BaseModel):
    query: str
    webSearchEnabled: bool = False
    preEmbeddingProcess: str = "pdr"
    sessionId: Optional[str] = None
    selectedFiles: Optional[List[str]] = None


class UploadRequest(BaseModel):
    file: str
    preEmbeddingProcess: str = "pdr"  # "none", "hype", "cch"


@router.post("/query")
async def handle_query(request: QueryRequest):
    """
    Kullanıcının gönderdiği sorguyu alır,
    pipeline üzerinden işler ve LLM yanıtını döner.
    """
    global request_counter
    try:  # Increment simple counter
        request_counter += 1

        query = request.query
        web_search_enabled = request.webSearchEnabled
        pre_embedding_process = request.preEmbeddingProcess
        session_id = request.sessionId
        selected_files = request.selectedFiles
        # Use system-level default search method
        search_method = DEFAULT_SEARCH_METHOD

        logger.info(f"📝 API Router received:")
        logger.info(f"   - Query: {query}")
        logger.info(f"   - Web Search Enabled: {web_search_enabled}")
        logger.info(f"   - Pre-embedding Process: {pre_embedding_process}")
        logger.info(f"   - Search Method (from config): {search_method}")
        logger.info(f"   - Session ID: {session_id}")
        logger.info(f"   - Selected Files: {selected_files}")

        answer = await run_orchestration(
            query,
            web_search_enabled,
            pre_embedding_process,
            session_id,
            selected_files,
            search_method,
        )
        logger.info(f"Processing query: {query[:100]}...")  # Log first 100 chars
        api_requests_total.labels(status="success").inc()

        logger.info("Query processed successfully")

        return {
            "response": answer.get("response"),
            "images": answer.get("images", []),
            "charts": answer.get("charts", []),
            "generatedFiles": answer.get("generatedFiles", []),
            "sessionId": answer.get("session_id", session_id),
        }

    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        api_requests_total.labels(status="error").inc()
        raise e


@router.post("/upload")
async def handle_upload(file: UploadFile = File(...)):
    global request_counter
    try:
        # Increment simple counter
        request_counter += 1

        logger.info(f"Starting file upload: {file.filename} ({file.content_type})")

        # Ensure uploads directory exists (use absolute path)
        uploads_dir = Path(UPLOADS_PATH)
        uploads_dir.mkdir(parents=True, exist_ok=True)

        # Save uploaded file
        file_path = uploads_dir / file.filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        logger.info(f"File saved to: {file_path}")

        # Process the uploaded file with pre-embedding process parameter
        from backend.pipeline.upload import process_file

        pre_embedding_process = "pdr"

        result = await process_file(
            str(file_path), pre_embedding_process=pre_embedding_process
        )

        logger.info(f"File processed successfully: {file.filename}")

        return {
            "filename": file.filename,
            "content_type": file.content_type,
            "status": "success",
            "message": "Dosya başarıyla yüklendi ve işlendi",
            "result": result,
            "preEmbeddingProcess": pre_embedding_process,
        }
    except Exception as e:
        error_message = str(e)
        logger.error(f"File upload error for {file.filename}: {error_message}")
        raise HTTPException(
            status_code=500, detail=f"Dosya yükleme hatası: {error_message}"
        )


@router.get("/chat/sessions")
def list_chat_sessions():
    """
    Returns a list of all chat sessions with metadata.
    """
    try:
        sessions = chat_history_manager.list_sessions()
        return {"sessions": sessions}
    except Exception as e:
        error_message = str(e)
        logger.error(f"Error listing chat sessions: {error_message}")
        raise HTTPException(
            status_code=500, detail=f"Error listing chat sessions: {error_message}"
        )


@router.get("/chat/sessions/{session_id}")
def get_chat_session(session_id: str):
    """
    Returns a specific chat session with all messages.
    """
    try:
        session = chat_history_manager.get_session(session_id)
        if not session:
            raise HTTPException(
                status_code=404, detail=f"Session {session_id} not found"
            )

        return {
            "session": {
                "session_id": session.session_id,
                "title": session.title,
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat(),
                "messages": [msg.to_dict() for msg in session.messages],
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        error_message = str(e)
        logger.error(f"Error getting chat session {session_id}: {error_message}")
        raise HTTPException(
            status_code=500, detail=f"Error getting chat session: {error_message}"
        )


@router.post("/chat/sessions")
def create_chat_session():
    """
    Creates a new chat session and returns its ID.
    """
    try:
        session = chat_history_manager.create_session()
        return {
            "session_id": session.session_id,
            "created_at": session.created_at.isoformat(),
        }
    except Exception as e:
        error_message = str(e)
        logger.error(f"Error creating chat session: {error_message}")
        raise HTTPException(
            status_code=500, detail=f"Error creating chat session: {error_message}"
        )


@router.delete("/chat/sessions/{session_id}")
def delete_chat_session(session_id: str):
    """
    Deletes a chat session and all its messages.
    """
    try:
        success = chat_history_manager.delete_session(session_id)
        if not success:
            raise HTTPException(
                status_code=404, detail=f"Session {session_id} not found"
            )

        return {"message": f"Session {session_id} deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        error_message = str(e)
        logger.error(f"Error deleting chat session {session_id}: {error_message}")
        raise HTTPException(
            status_code=500, detail=f"Error deleting chat session: {error_message}"
        )


@router.get("/files")
def list_files():
    """
    Returns a list of files in the uploads directory with metadata.
    """
    try:
        uploads_dir = Path(UPLOADS_PATH)
        if not uploads_dir.exists():
            return {"files": []}  # Return an empty list if the directory doesn't exist

        # Import the temporary file check function
        from backend.utils.preview import PreviewGenerator

        files = []
        for file in uploads_dir.iterdir():
            if file.is_file():
                # Skip temporary files
                if PreviewGenerator._is_temporary_file(str(file)):
                    continue

                files.append(
                    {
                        "name": file.name,
                        "size": file.stat().st_size,  # File size in bytes
                        "created_at": datetime.fromtimestamp(
                            file.stat().st_ctime
                        ).isoformat(),  # Creation time in ISO 8601
                        "modified_at": datetime.fromtimestamp(
                            file.stat().st_mtime
                        ).isoformat(),  # Last modification time in ISO 8601
                    }
                )
        return {"files": files}
    except Exception as e:
        error_message = str(e)
        raise HTTPException(
            status_code=500, detail=f"Error listing files: {error_message}"
        )


@router.get("/created-documents")
def list_created_documents():
    """
    Returns a list of files in the created_documents directory with metadata.
    """
    try:
        created_documents_dir = Path(CREATED_DOCUMENTS_PATH)
        if not created_documents_dir.exists():
            return {"files": []}  # Return an empty list if the directory doesn't exist

        files = []
        for file in created_documents_dir.iterdir():
            if file.is_file():
                files.append(
                    {
                        "name": file.name,
                        "size": file.stat().st_size,  # File size in bytes
                        "created_at": datetime.fromtimestamp(
                            file.stat().st_ctime
                        ).isoformat(),  # Creation time in ISO 8601
                        "modified_at": datetime.fromtimestamp(
                            file.stat().st_mtime
                        ).isoformat(),  # Last modification time in ISO 8601
                    }
                )
        return {"files": files}
    except Exception as e:
        error_message = str(e)
        raise HTTPException(
            status_code=500, detail=f"Error listing created documents: {error_message}"
        )


@router.get("/metrics")
def get_metrics():
    """
    Returns system metrics and analytics data.
    """
    try:
        # Get file count
        uploads_dir = Path(UPLOADS_PATH)
        file_count = (
            len([f for f in uploads_dir.iterdir() if f.is_file()])
            if uploads_dir.exists()
            else 0
        )

        # Get vector store info
        vectorstore_exists = Path(VECTORSTORE_PATH_STR).exists()

        # Simple request counter - use module variable
        global request_counter
        total_requests = request_counter

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
                    "icon": "fas fa-file-upload",
                },
                {
                    "title": "Query answered",
                    "time": "5 minutes ago",
                    "icon": "fas fa-comment",
                },
                {
                    "title": "System started",
                    "time": "1 hour ago",
                    "icon": "fas fa-power-off",
                },
            ],
        }
    except Exception as e:
        error_message = str(e)
        raise HTTPException(
            status_code=500, detail=f"Error fetching metrics: {error_message}"
        )


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
        uploads_dir = Path(UPLOADS_PATH)
        file_path = uploads_dir / filename

        logger.debug(f"Checking file existence: {file_path}")
        logger.debug(f"File exists: {file_path.exists()}")

        if not file_path.exists():
            logger.error(f"File not found: {filename}")
            raise HTTPException(status_code=404, detail=f"File '{filename}' not found")

        # Load vector store and PII mappings
        if not Path(VECTORSTORE_PATH_STR).exists():
            # If no vector store exists, just delete the file
            logger.warning(f"No vector store found, deleting file only: {filename}")
            file_path.unlink()
            logger.info(f"File deleted successfully: {filename}")
            return {
                "message": f"File '{filename}' deleted successfully (no vector store found)"
            }

        # Load existing vector store
        import json

        # Stem file name
        base_filename = Path(filename).stem

        # Remove chunks from PII maps
        pii_map_path = MASKED_MAP_JSON_PATH
        if pii_map_path.exists():
            with open(pii_map_path, "r", encoding="utf-8") as f:
                pii_maps = json.load(f)
            pii_delete_count = 0
            chunk_ids_to_delete = [
                (chunk_id, chunk_map)
                for chunk_id, chunk_map in pii_maps.items()
                if base_filename in chunk_id
            ]
            for chunk_id, chunk_map in chunk_ids_to_delete:
                pii_maps.pop(chunk_id, None)
                pii_delete_count += len(chunk_map)
            with open(pii_map_path, "w", encoding="utf-8") as f:
                json.dump(pii_maps, f, ensure_ascii=False, indent=2)

        try:
            from backend.retrieval.retriever import load_vectorstore

            client = load_vectorstore(VECTORSTORE_PATH_STR)
            logger.info(f"Vector store loaded successfully")

            client.delete(
                collection_name="test_collection",
                points_selector=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="metadata.file_name",
                            match=models.MatchValue(value=base_filename),
                        )
                    ]
                ),
            )
            client.close()
        except Exception as e:
            logger.error(f"Error deleting chunks from vector store: {e}")

        # Also remove documents from keyword search index
        try:
            from backend.retrieval.keyword_search import get_keyword_search

            logger.info(
                f"🔍 Removing documents from keyword search index for file: {base_filename}"
            )
            keyword_search = get_keyword_search()
            keyword_search.remove_documents_by_file(base_filename)
            keyword_search.save_index()
            logger.info(f"✅ Documents removed from keyword search index")
        except Exception as e:
            logger.error(f"Error deleting documents from keyword search index: {e}")

        # Delete the actual file
        logger.info(f"🗑️ Deleting physical file: {file_path}")
        file_path.unlink()
        logger.info(f"✅ Physical file deleted successfully: {filename}")

        result = {
            "message": f"File '{filename}' deleted successfully",
            "chunks_deleted": len(chunk_ids_to_delete),
            "pii_entries_removed": pii_delete_count,
            "file_path": str(file_path),
        }
        logger.info(f"🎉 Deletion completed successfully: {result}")
        return result

    except HTTPException:
        logger.error(f"❌ HTTP Exception during deletion: {filename}")
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error deleting file '{filename}': {str(e)}")
        import traceback

        logger.error(f"❌ Traceback: {traceback.format_exc()}")

        raise HTTPException(status_code=500, detail=f"Error deleting file: {str(e)}")


@router.get("/files/{filename}/download")
def download_file(filename: str):
    """
    Download a file from uploads directory.
    """
    try:
        file_path = Path(UPLOADS_PATH) / filename

        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"File '{filename}' not found")

        return FileResponse(
            path=file_path, filename=filename, media_type="application/octet-stream"
        )
    except Exception as e:
        error_message = str(e)
        logger.error(f"Error downloading file {filename}: {error_message}")
        raise HTTPException(
            status_code=500, detail=f"Error downloading file: {error_message}"
        )


@router.get("/files/{filename}")
def get_file_info(filename: str):
    """
    Get information about a specific file.
    """
    try:
        file_path = Path(UPLOADS_PATH) / filename

        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"File '{filename}' not found")

        stats = file_path.stat()
        return {
            "name": filename,
            "size": stats.st_size,
            "created_at": datetime.fromtimestamp(stats.st_ctime).isoformat(),
            "modified_at": datetime.fromtimestamp(stats.st_mtime).isoformat(),
        }
    except Exception as e:
        error_message = str(e)
        logger.error(f"Error getting file info {filename}: {error_message}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting file info: {error_message}",
        )


@router.get("/files/{filename}/preview")
def get_file_preview(filename: str):
    """
    Generate a preview for the specified file.
    Returns different preview types based on file extension.
    """
    try:
        file_path = Path(UPLOADS_PATH) / filename

        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"File '{filename}' not found")

        from backend.utils.preview import PreviewGenerator

        preview_generator = PreviewGenerator(str(file_path))
        preview_data = preview_generator.generate_preview()

        return {
            "filename": filename,
            "preview_type": preview_data["type"],
            "preview_data": preview_data["data"],
            "success": True,
        }
    except Exception as e:
        error_message = str(e)
        logger.error(f"Error generating preview for {filename}: {error_message}")
        raise HTTPException(
            status_code=500, detail=f"Error generating preview: {error_message}"
        )


@router.get("/created-documents/{filename}/download")
def download_created_document(filename: str):
    """
    Download a file from created_documents directory.
    """
    try:
        file_path = Path(CREATED_DOCUMENTS_PATH) / filename

        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"File '{filename}' not found")

        return FileResponse(
            path=file_path, filename=filename, media_type="application/octet-stream"
        )
    except Exception as e:
        error_message = str(e)
        logger.error(f"Error downloading created document {filename}: {error_message}")
        raise HTTPException(
            status_code=500,
            detail=f"Error downloading created document: {error_message}",
        )


@router.get("/created-documents/{filename}")
def get_created_document_info(filename: str):
    """
    Get information about a specific created document.
    """
    try:
        file_path = Path(CREATED_DOCUMENTS_PATH) / filename

        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"File '{filename}' not found")

        stats = file_path.stat()
        return {
            "name": filename,
            "size": stats.st_size,
            "created_at": datetime.fromtimestamp(stats.st_ctime).isoformat(),
            "modified_at": datetime.fromtimestamp(stats.st_mtime).isoformat(),
        }
    except Exception as e:
        error_message = str(e)
        logger.error(f"Error getting created document info {filename}: {error_message}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting created document info: {error_message}",
        )


@router.get("/created-documents/{filename}/preview")
def get_created_document_preview(filename: str):
    """
    Generate a preview for the specified created document.
    Returns different preview types based on file extension.
    """
    try:
        file_path = Path(CREATED_DOCUMENTS_PATH) / filename

        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"File '{filename}' not found")

        from backend.utils.preview import PreviewGenerator

        preview_generator = PreviewGenerator(str(file_path))
        preview_data = preview_generator.generate_preview()

        return {
            "filename": filename,
            "preview_type": preview_data["type"],
            "preview_data": preview_data["data"],
            "success": True,
        }
    except Exception as e:
        error_message = str(e)
        logger.error(
            f"Error generating preview for created document {filename}: {error_message}"
        )
        raise HTTPException(
            status_code=500, detail=f"Error generating preview: {error_message}"
        )


@router.delete("/created-documents/{filename}")
def delete_created_document(filename: str):
    """
    Delete a created document from local storage.
    """
    try:
        file_path = Path(CREATED_DOCUMENTS_PATH) / filename

        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"File '{filename}' not found")

        # Delete the file
        file_path.unlink()

        logger.info(f"Created document deleted successfully: {filename}")

        return {
            "message": f"Created document '{filename}' deleted successfully",
            "success": True,
        }
    except Exception as e:
        error_message = str(e)
        logger.error(f"Error deleting created document {filename}: {error_message}")
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting created document: {error_message}",
        )


@router.get("/finance-news")
async def get_finance_news():
    """
    Fetch latest finance news from nance RSS feed."""
    try:
        news_articles = fetch_and_parse_news()
        # Limit to 20 most recent articles
        news_articles = news_articles[:20]

        logger.info(f"Successfully fetched {len(news_articles)} finance news articles")

        return {
            "status": "success",
            "count": len(news_articles),
            "articles": news_articles,
            "last_updated": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error fetching finance news: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error fetching finance news: {str(e)}"
        )


# Document Verification Endpoints
@router.post("/verify")
async def verify_document(
    file: UploadFile = File(...),
    verification_type: str = "auto",
):
    """
    Verify a document using the LLM-based verification pipeline with Wolfram Alpha mathematical verification (always enabled)
    """
    global request_counter
    try:
        # Increment request counter
        request_counter += 1

        logger.info(
            f"Starting document verification: {file.filename} (type: {verification_type})"
        )

        # Check file type
        allowed_extensions = [".pdf", ".jpg", ".jpeg", ".png", ".tiff", ".bmp"]
        file_ext = Path(file.filename).suffix.lower()

        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {file_ext}. Allowed types: {', '.join(allowed_extensions)}",
            )

        # Create verification_uploads directory if it doesn't exist
        verification_dir = Path(VERIFICATION_UPLOADS_PATH)
        verification_dir.mkdir(parents=True, exist_ok=True)

        # Save uploaded file temporarily
        temp_file_path = verification_dir / file.filename
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        logger.info(f"File saved for verification: {temp_file_path}")

        # Import and run verification function
        from backend.utils.verification import verify_document

        # Run verification
        verification_result = await verify_document(str(temp_file_path))

        # Clean up temporary file
        try:
            temp_file_path.unlink()
            logger.info(f"Temporary file cleaned up: {temp_file_path}")
        except Exception as cleanup_error:
            logger.warning(f"Could not clean up temporary file: {cleanup_error}")

        logger.info(
            f"Document verification completed: {verification_result.get('status', 'unknown')}"
        )

        return verification_result

    except Exception as e:
        error_message = str(e)
        logger.error(
            f"Document verification error for {file.filename}: {error_message}"
        )

        # Clean up temporary file on error
        try:
            if "temp_file_path" in locals():
                temp_file_path.unlink()
        except:
            pass
        raise HTTPException(
            status_code=500, detail=f"Document verification failed: {error_message}"
        )


@router.get("/verification-types")
def get_verification_types():
    """
    Get available document verification types
    """
    try:
        verification_types = [
            "invoice",
            "receipt",
            "bank_statement",
            "payslip",
            "contract",
            "tax_declaration",
            "expense_voucher",
            "other",
            "auto",
        ]

        return {
            "verification_types": verification_types,
            "supported_formats": [".pdf", ".jpg", ".jpeg", ".png", ".tiff", ".bmp"],
            "default_type": "auto",
        }

    except Exception as e:
        error_message = str(e)
        logger.error(f"Error getting verification types: {error_message}")
        raise HTTPException(
            status_code=500, detail=f"Error getting verification types: {error_message}"
        )
