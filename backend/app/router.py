from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from backend.pipeline.query import run_orchestration, run_news_chat_orchestration, run_graph_orchestration
from backend.core.tools.balance import process_balance_of_payments
from backend.core.chat import chat_history_manager
from backend.monitoring.metrics import api_requests_total
from backend.shared.logger import get_logger
from backend.shared.constants import (
    UPLOADS_PATH,
    VECTORSTORE_PATH_STR,
    MASKED_MAP_JSON_PATH,
    CREATED_DOCUMENTS_PATH,
    IMAGES_PATH_STR,
    ALLOWED_FILE_EXTENSIONS,
)
import shutil
from pathlib import Path
from datetime import date, datetime, timedelta
from typing import List, Optional
from dateutil.relativedelta import relativedelta
from backend.utils.news import get_aggregated_financial_news
from backend.utils.market_data import store, refresh_eod
from qdrant_client import models
from backend.utils.preview import PreviewGenerator
from backend.utils.balance_payments_database import balance_payments_db

logger = get_logger("ROUTER")
router = APIRouter()


def delete_document_images(filename: str) -> dict:
    """
    Delete all images associated with a document using the JSON mapping.

    Args:
        filename: The document filename (with or without extension)

    Returns:
        dict: Information about the deletion operation
    """
    try:
        import json

        # Extract document name without extension
        document_name = Path(filename).stem

        # Load image mapping
        mapping_file = Path(IMAGES_PATH_STR) / "image_document_mapping.json"
        if not mapping_file.exists():
            logger.info(f"📁 No image mapping file found for document: {document_name}")
            return {
                "images_deleted": 0,
                "mapping_updated": False,
                "message": "No image mapping file found",
            }

        with open(mapping_file, "r", encoding="utf-8") as f:
            mapping = json.load(f)

        # Find images associated with this document
        images_to_delete = []
        for image_filename, image_info in mapping.items():
            if image_info.get("document") == document_name:
                images_to_delete.append(image_filename)

        # Delete the image files
        deleted_count = 0
        for image_filename in images_to_delete:
            image_path = Path(IMAGES_PATH_STR) / image_filename
            if image_path.exists():
                image_path.unlink()
                deleted_count += 1

        # Remove entries from mapping
        for image_filename in images_to_delete:
            mapping.pop(image_filename, None)

        # Save updated mapping
        with open(mapping_file, "w", encoding="utf-8") as f:
            json.dump(mapping, f, indent=2, ensure_ascii=False)

        logger.info(f"🗂️ Deleted {deleted_count} images for document: {document_name}")
        return {
            "images_deleted": deleted_count,
            "mapping_updated": True,
            "message": f"Deleted {deleted_count} images for document {document_name}",
        }

    except Exception as e:
        logger.error(f"❌ Error deleting images for {filename}: {e}")
        return {"images_deleted": 0, "mapping_updated": False, "error": str(e)}


class QueryRequest(BaseModel):
    query: str
    webSearchEnabled: bool = False
    preEmbeddingProcess: str = "none"
    sessionId: Optional[str] = None
    selectedFiles: Optional[List[str]] = None
    agentMode: str = "standard"  # "standard" or "graph"


class NewsChatRequest(BaseModel):
    query: str
    news_context: dict
    sessionId: Optional[str] = None
    selectedFiles: Optional[List[str]] = None


class UploadRequest(BaseModel):
    file: str
    preEmbeddingProcess: str = "none"  # "none", "cch"


class BalanceProcessRequest(BaseModel):
    fileName: str
    replaceExisting: bool = True


@router.get("/market/eod")
async def get_market_eod(symbol: str = "TUPRS.IS", limit: int = 7):
    logger.info(f"Getting market EOD for {symbol} with limit {limit}")
    try:
        data = store.get_latest_quotes(symbol, limit)
        return {"symbol": symbol, "count": len(data), "data": data}
    except Exception as e:
        logger.error(f"Error fetching EOD from DB: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/market/company-info")
async def get_company_info(symbol: str = "TUPRS.IS"):
    logger.info(f"Getting company info for {symbol}")
    try:
        data = store.get_company_info(symbol)
        return {"symbol": symbol, "data": data}
    except Exception as e:
        logger.error(f"Error fetching company info from DB: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/market/eod/refresh")
async def refresh_market_eod(symbols: str = "TUPRS.IS", limit: int = 7):
    logger.info("Refreshing market EOD")
    try:
        saved = await refresh_eod(symbols=symbols, limit=limit)
        return {"status": "ok", "saved": saved}
    except Exception as e:
        logger.error(f"Error refreshing EOD: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/market/most-changed")
async def get_most_changed_quotes(request: dict):
    logger.info("Getting most changed quotes")
    try:
        symbols = request.get("symbols", [])
        limit = request.get("limit", 30)
        chart_num = request.get("chart_num", 8)

        data = store.get_most_changed_quotes(symbols, limit, chart_num)
        return {"data": data}
    except Exception as e:
        logger.error(f"Error getting most changed quotes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/market/gainers-losers-active")
async def get_gainers_losers_active(request: dict):
    logger.info("Getting gainers/losers/active")
    try:
        symbols = request.get("symbols", [])
        limit = request.get("limit", 30)
        chart_num = request.get("chart_num", 8)

        data = store.get_gainers_losers_active(symbols, limit, chart_num)
        return {"data": data}
    except Exception as e:
        logger.error(f"Error getting gainers/losers/active: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/market/search-symbols")
async def search_symbols(query: str = ""):
    logger.info("Searching symbols")
    try:
        data = store.search_symbols(query)
        return {"data": data}
    except Exception as e:
        logger.error(f"Error searching symbols: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query")
async def handle_query(request: QueryRequest):
    """
    Receives the user's query,
    processes it through the pipeline, and returns the LLM response.
    
    Supports two agent modes:
    - "standard": Uses the main agent with optional web search
    - "graph": Uses the LangGraph-based agent with planning, approval, and synthesis
    """
    try:

        query = request.query
        web_search_enabled = request.webSearchEnabled
        session_id = request.sessionId
        selected_files = request.selectedFiles
        agent_mode = request.agentMode

        logger.info(f"📨 Query received in {agent_mode} mode: {query[:50]}...")

        if agent_mode == "graph":
            # Use LangGraph-based agent pipeline
            answer = await run_graph_orchestration(
                query,
                session_id,
                selected_files,
            )
        else:
            # Use standard agent pipeline
            answer = await run_orchestration(
                query,
                web_search_enabled,
                session_id,
                selected_files,
            )
        api_requests_total.labels(status="success").inc()

        return {
            "response": answer.get("response"),
            "images": answer.get("images", []),
            "charts": answer.get("charts", []),
            "generatedFiles": answer.get("generatedFiles", []),
            "sources": answer.get("sources", []),
            "sessionId": answer.get("session_id", session_id),
        }

    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        api_requests_total.labels(status="error").inc()
        raise e


@router.post("/news-chat")
async def handle_news_chat(request: NewsChatRequest):
    """
    Handle news-specific chat queries with news context and web search capabilities.
    """
    try:
        query = request.query
        news_context = request.news_context
        session_id = request.sessionId

        logger.info(f"📰 News Chat API Router received:")
        logger.info(f"   - Query: {query}")
        logger.info(f"   - News Title: {news_context.get('title', 'Unknown')}")
        logger.info(f"   - Session ID: {session_id}")

        # Process news chat query
        answer = await run_news_chat_orchestration(query, news_context, session_id)
        api_requests_total.labels(status="success").inc()

        return {
            "status": "success",
            "response": answer.get("response"),
            "images": answer.get("images", []),
            "sessionId": answer.get("session_id", session_id),
        }

    except Exception as e:
        logger.error(f"Error processing news chat query: {str(e)}")
        api_requests_total.labels(status="error").inc()
        raise HTTPException(
            status_code=500, detail=f"Error processing news chat query: {str(e)}"
        )


@router.post("/upload")
async def handle_upload(
    file: UploadFile = File(...),
    photoLessMode: bool = Form(False),
):
    try:

        # Ensure uploads directory exists (use absolute path)
        uploads_dir = Path(UPLOADS_PATH)
        uploads_dir.mkdir(parents=True, exist_ok=True)

        # Save uploaded file
        file_path = uploads_dir / file.filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Process the uploaded file with pre-embedding process parameter
        from backend.pipeline.upload import process_file

        pre_embedding_process = "cch"

        result = await process_file(
            str(file_path),
            pre_embedding_process=pre_embedding_process,
            photo_less_mode=photoLessMode,
        )

        logger.info(f"File processed successfully: {file.filename}")

        return {
            "filename": file.filename,
            "content_type": file.content_type,
            "status": "success",
            "message": "Dosya başarıyla yüklendi ve işlendi",
            "result": result,
            "preEmbeddingProcess": pre_embedding_process,
            "photoLessMode": photoLessMode,
        }
    except Exception as e:
        error_message = str(e)
        logger.error(f"File upload error for {file.filename}: {error_message}")
        raise HTTPException(
            status_code=500, detail=f"Dosya yükleme hatası: {error_message}"
        )


@router.post("/balance-of-payments/upload")
async def handle_balance_upload(
    file: UploadFile = File(...),
    photoLessMode: bool = Form(False),
):
    """Store balance-of-payments documents without triggering vector ingestion."""

    filename = getattr(file, "filename", "unknown")

    try:
        uploads_dir = Path(UPLOADS_PATH)
        uploads_dir.mkdir(parents=True, exist_ok=True)

        file_path = uploads_dir / filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        logger.info(
            "Balance document stored for agent-only processing: %s (photoLessMode=%s)",
            filename,
            photoLessMode,
        )

        return {
            "filename": filename,
            "content_type": file.content_type,
            "status": "success",
            "message": "Balance document stored for agent processing",
            "photoLessMode": photoLessMode,
        }
    except Exception as e:
        error_message = str(e)
        logger.error(
            "Balance document upload failed for %s: %s",
            filename,
            error_message,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Balance document upload failed: {error_message}",
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
        logger.error(f"Error getting chat session {session_id}: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error getting chat session: {str(e)}"
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
            status_code=500, detail=f"Error listing created documents: {error_message}"
        )


@router.delete("/files/{filename}")
def delete_file(filename: str):
    """
    Delete a file from uploads directory and remove its chunks from vector store.
    """
    try:
        logger.info(f"Starting deletion for file '{filename}'")
        # Check if file exists in uploads directory
        uploads_dir = Path(UPLOADS_PATH)
        file_path = uploads_dir / filename

        logger.debug(f"File exists: {file_path.exists()}")

        if not file_path.exists():
            logger.error(f"File not found: {filename}")
            raise HTTPException(status_code=404, detail=f"File '{filename}' not found")

        # Load vector store and PII mappings
        if not Path(VECTORSTORE_PATH_STR).exists():
            # If no vector store exists, just delete the file
            logger.warning(f"No vector store found, deleting file only: {filename}")
            file_path.unlink()

            # Delete corresponding images
            image_deletion_result = delete_document_images(filename)

            return {
                "message": f"File '{filename}' deleted successfully (no vector store found)",
                "images_deleted": image_deletion_result["images_deleted"],
                "mapping_updated": image_deletion_result["mapping_updated"],
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
            from backend.retrieval.retriever import get_vectorstore

            client = get_vectorstore()
            if client is not None:
                logger.info(f"Vector store loaded successfully")
                client.delete(
                    collection_name="documents",
                    points_selector=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="metadata.file_name",
                                match=models.MatchValue(value=base_filename),
                            )
                        ]
                    ),
                )
            else:
                logger.warning("Vector store client not available for deletion")
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
        except Exception as e:
            logger.error(f"Error deleting documents from keyword search index: {e}")

        # Delete the actual file
        file_path.unlink()

        # Delete corresponding images
        image_deletion_result = delete_document_images(filename)

        result = {
            "message": f"File '{filename}' deleted successfully",
            "chunks_deleted": len(chunk_ids_to_delete),
            "pii_entries_removed": pii_delete_count,
            "file_path": str(file_path),
            "images_deleted": image_deletion_result["images_deleted"],
            "mapping_updated": image_deletion_result["mapping_updated"],
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

        preview_generator = PreviewGenerator(str(file_path))
        preview_data = preview_generator.generate_preview()

        return {
            "filename": filename,
            "preview_type": preview_data["type"],
            "preview_data": preview_data["data"],
            "success": True,
        }
    except Exception as e:
        logger.error(f"Error generating preview for {filename}: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error generating preview: {str(e)}"
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
        raise HTTPException(
            status_code=500,
            detail=f"Error getting created document info: {str(e)}",
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

        preview_generator = PreviewGenerator(str(file_path))
        preview_data = preview_generator.generate_preview()

        return {
            "filename": filename,
            "preview_type": preview_data["type"],
            "preview_data": preview_data["data"],
            "success": True,
        }
    except Exception as e:
        logger.error(
            f"Error generating preview for created document {filename}: {str(e)}"
        )
        raise HTTPException(
            status_code=500, detail=f"Error generating preview: {str(e)}"
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

        # Delete corresponding images
        image_deletion_result = delete_document_images(filename)

        logger.info(f"Created document deleted successfully: {filename}")

        return {
            "message": f"Created document '{filename}' deleted successfully",
            "success": True,
            "images_deleted": image_deletion_result["images_deleted"],
            "mapping_updated": image_deletion_result["mapping_updated"],
        }
    except Exception as e:
        error_message = str(e)
        logger.error(f"Error deleting created document {filename}: {error_message}")
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting created document: {error_message}",
        )


@router.post("/balance-of-payments/process")
async def trigger_balance_of_payments_process(request: BalanceProcessRequest):
    file_path = Path(UPLOADS_PATH) / request.fileName

    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"File {request.fileName} not found in uploads directory",
        )

    suffix = file_path.suffix.lower()
    if suffix not in ALLOWED_FILE_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                "Balance of payments processing currently supports files with extensions: "
                + ", ".join(sorted(ALLOWED_FILE_EXTENSIONS))
            ),
        )

    try:
        result = await process_balance_of_payments(file_path=str(file_path))

        return result
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Failed to process balance of payments workbook",
        )


@router.get("/balance-of-payments/calendar")
def get_balance_of_payments_calendar(
    months: int = 3,
    endDate: Optional[str] = None,
):
    months = max(1, min(months, 12))

    latest_activity_str = balance_payments_db.latest_activity_date()
    latest_activity: Optional[date] = None
    if latest_activity_str:
        try:
            latest_activity = datetime.fromisoformat(latest_activity_str).date()
        except ValueError:
            logger.warning(
                "Invalid latest activity date stored in database: %s",
                latest_activity_str,
            )

    if endDate:
        try:
            end_date = datetime.fromisoformat(endDate).date()
        except ValueError:
            raise HTTPException(
                status_code=400, detail="Invalid endDate format. Use YYYY-MM-DD"
            )
    else:
        # Use today's date as the end date for calendar view
        end_date = datetime.today().date()

    # Calculate start date by going back 'months' number of months
    start_date = end_date.replace(day=1) - relativedelta(months=months - 1)

    end_weekday = end_date.weekday()
    if end_weekday != 6:  # extend to Sunday for full week display
        end_date = end_date + timedelta(days=(6 - end_weekday))

    if start_date > end_date:
        start_date = end_date

    daily_balances = balance_payments_db.get_daily_balances(start_date, end_date)
    max_absolute = max((abs(day["net"]) for day in daily_balances), default=0.0)

    return {
        "startDate": start_date.isoformat(),
        "endDate": end_date.isoformat(),
        "days": daily_balances,
        "maxAbsoluteNet": max_absolute,
        "latestActivity": latest_activity_str,
    }


@router.get("/balance-of-payments/transactions/{date_str}")
def get_balance_transactions_for_day(date_str: str):
    try:
        target_date = datetime.fromisoformat(date_str).date()
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid date format. Use YYYY-MM-DD",
        )

    transactions = balance_payments_db.get_transactions_for_date(target_date)
    return {
        "date": target_date.isoformat(),
        "transactions": transactions,
    }


@router.get("/balance-of-payments/category-totals")
def get_balance_category_totals():
    """
    Get transaction totals grouped by category.
    All amounts are treated as positive (absolute values).
    """
    try:
        category_totals = balance_payments_db.get_category_totals()
        return {
            "categories": category_totals,
        }
    except Exception as e:
        logger.error(f"Error fetching category totals: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch category totals",
        )


@router.get("/balance-of-payments/category-net-values")
def get_balance_category_net_values():
    """
    Get net values (income - expense) for each category.
    Returns income, expense, and net amounts for each category.
    """
    try:
        category_net_values = balance_payments_db.get_category_net_values()
        return {
            "categories": category_net_values,
        }
    except Exception as e:
        logger.error(f"Error fetching category net values: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch category net values",
        )


@router.get("/finance-news")
async def get_finance_news(force_refresh: bool = False):
    """
    Fetch aggregated financial news from multiple Turkish sources with intelligent clustering.
    This endpoint provides Perplexity.ai-style news discovery with multi-source story detection.

    Args:
        force_refresh: If True, fetch new articles and update database. If False, load from database.
    """
    try:
        # Use the enhanced multi-source aggregation system
        news_response = await get_aggregated_financial_news(force_refresh=force_refresh)

        logger.info(
            f"Successfully fetched aggregated financial news: {news_response.total_articles} total articles, {news_response.total_clusters} clusters"
        )

        # Create backward-compatible articles array for existing frontend
        # TEMPORARILY: Show only clustered articles (multi-source stories)
        all_articles = []

        # Add ALL clustered articles (remove limit to see all multi-source stories)
        for (
            cluster
        ) in news_response.clustered_articles:  # Show all clusters, not just top 10
            # Take the first article from each cluster as representative
            if cluster.articles:
                # CREATE A COPY to avoid modifying the original article in cluster data
                from copy import deepcopy

                representative_article = deepcopy(cluster.articles[0])

                # Add cluster info to the article
                representative_article.title = cluster.unified_title
                representative_article.summary = cluster.unified_description

                # Add available images from the cluster for frontend display
                if hasattr(cluster, "available_images") and cluster.available_images:
                    representative_article.available_images = cluster.available_images

                # Use the earliest publication date from all sources in the cluster
                representative_article.published = (
                    cluster.published_earliest
                    if cluster.published_earliest
                    else representative_article.published
                )

                # Show multiple sources (up to 3, then add ...)
                sources = (
                    cluster.sources
                    if hasattr(cluster, "sources")
                    else [article.source for article in cluster.articles]
                )
                unique_sources = list(
                    dict.fromkeys(sources)
                )  # Remove duplicates while preserving order

                if len(unique_sources) <= 3:
                    representative_article.source = ", ".join(unique_sources)
                else:
                    representative_article.source = (
                        ", ".join(unique_sources[:3]) + "..."
                    )

                all_articles.append(representative_article)

        # TEMPORARILY: Skip single articles to focus on multi-source clustering
        # remaining_slots = 20 - len(all_articles)
        # all_articles.extend(news_response.single_articles[:remaining_slots])

        return {
            "status": "success",
            # Enhanced structure for future frontend updates
            "clustered_articles": news_response.clustered_articles,
            "single_articles": [],  # TEMPORARILY hidden to focus on clustering
            "total_clusters": news_response.total_clusters,
            "total_articles": news_response.total_articles,
            "sources_count": 13,  # Number of Turkish financial news sources
            "feature": "multi_source_clustering_only",  # Temporary mode
            "clustering_method": "llm-based",
            "display_mode": "clustered_only",  # Indicator we're hiding single articles
            # Backward compatibility for existing frontend
            "articles": all_articles,  # Only clustered articles now
            "count": len(all_articles),
            "last_updated": news_response.last_updated,
        }

    except Exception as e:
        logger.error(f"Error fetching aggregated finance news: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error fetching finance news: {str(e)}"
        )


@router.get("/finance-news/sources")
async def get_finance_news_sources():
    """
    Get information about all configured financial news sources.
    """
    try:
        from backend.utils.news import FINANCIAL_NEWS_SOURCES

        sources_info = []
        for source in FINANCIAL_NEWS_SOURCES:
            sources_info.append(
                {"name": source.name, "language": source.language, "active": True}
            )

        return {
            "status": "success",
            "total_sources": len(FINANCIAL_NEWS_SOURCES),
            "sources": sources_info,
            "last_updated": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error fetching news sources info: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error fetching news sources: {str(e)}"
        )
