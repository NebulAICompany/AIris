from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from backend.pipeline.query import run_orchestration, run_news_chat_orchestration, run_orchestration_stream
from backend.core.chat import chat_history_manager
from backend.shared.logger import get_logger
from backend.shared.constants import (
    UPLOADS_PATH,
    VECTORSTORE_PATH_STR,
    CREATED_DOCUMENTS_PATH,
    IMAGES_PATH_STR,
    ALLOWED_FILE_EXTENSIONS,
)
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Optional
from backend.utils.news import get_aggregated_financial_news
from backend.utils.market_data import store, refresh_eod
from qdrant_client import models
from backend.utils.preview import PreviewGenerator
from backend.utils.uploads_database import uploads_db
from backend.retrieval.retriever import get_vectorstore
from backend.retrieval.keyword_search import get_keyword_search
import json

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
    useSpdrag: bool = False
    preEmbeddingProcess: str = "none"
    sessionId: Optional[str] = None
    selectedFiles: Optional[List[str]] = None


class NewsChatRequest(BaseModel):
    query: str
    news_context: dict
    sessionId: Optional[str] = None
    selectedFiles: Optional[List[str]] = None


class UpdateChatSessionRequest(BaseModel):
    title: Optional[str] = None


class UploadRequest(BaseModel):
    file: str
    preEmbeddingProcess: str = "none"  # "none", "cch"


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
    """
    try:

        query = request.query
        web_search_enabled = request.webSearchEnabled
        use_spdrag = request.useSpdrag
        session_id = request.sessionId
        selected_files = request.selectedFiles

        answer = await run_orchestration(
            query,
            web_search_enabled,
            use_spdrag,
            session_id,
            selected_files,
        )

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
        raise e


@router.post("/query/stream")
async def handle_query_stream(request: QueryRequest):
    """
    Streaming version of /query endpoint using Server-Sent Events (SSE).
    Returns real-time token-by-token response from the LLM.
    """
    try:
        query = request.query
        web_search_enabled = request.webSearchEnabled
        use_spdrag = request.useSpdrag
        session_id = request.sessionId
        selected_files = request.selectedFiles
        if use_spdrag:
            logger.info(
                "query/stream: useSpdrag=True, selectedFiles count=%s",
                len(selected_files) if selected_files else 0,
            )

        return StreamingResponse(
            run_orchestration_stream(
                query,
                web_search_enabled,
                use_spdrag,
                session_id,
                selected_files,
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    except Exception as e:
        logger.error(f"Error processing streaming query: {str(e)}")
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

        return {
            "status": "success",
            "response": answer.get("response"),
            "images": answer.get("images", []),
            "sessionId": answer.get("session_id", session_id),
        }

    except Exception as e:
        logger.error(f"Error processing news chat query: {str(e)}")
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
            "message": "File uploaded and processed successfully",
            "result": result,
            "preEmbeddingProcess": pre_embedding_process,
            "photoLessMode": photoLessMode,
        }
    except Exception as e:
        error_message = str(e)
        logger.error(f"File upload error for {file.filename}: {error_message}")
        raise HTTPException(
            status_code=500, detail=f"File upload error: {error_message}"
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


@router.put("/chat/sessions/{session_id}")
def update_chat_session(session_id: str, request: UpdateChatSessionRequest):
    """
    Updates a chat session.
    """
    try:
        session = chat_history_manager.update_session(session_id, title=request.title)
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
        logger.error(f"Error updating chat session {session_id}: {error_message}")
        raise HTTPException(
            status_code=500, detail=f"Error updating chat session: {error_message}"
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
async def delete_file(filename: str):
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

        # Load vector store
        if not Path(VECTORSTORE_PATH_STR).exists():
            # If no vector store exists, just delete the file
            logger.warning(f"No vector store found, deleting file only: {filename}")
            file_path.unlink()

            # Delete corresponding images
            image_deletion_result = delete_document_images(filename)

            # Remove from uploads database
            try:
                uploads_db.delete_upload_record(filename)
            except Exception as e:
                logger.warning(f"Failed to delete upload record from database: {e}")

            return {
                "message": f"File '{filename}' deleted successfully (no vector store found)",
                "images_deleted": image_deletion_result["images_deleted"],
                "mapping_updated": image_deletion_result["mapping_updated"],
            }

        # Stem file name
        base_filename = Path(filename).stem

        chunk_ids_to_delete = []

        try:
            client = get_vectorstore()
            if client is not None:
                logger.info(f"Vector store loaded successfully")
                await client.delete(
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

        # Remove from uploads database
        try:
            uploads_db.delete_upload_record(filename)
        except Exception as e:
            logger.warning(f"Failed to delete upload record from database: {e}")

        result = {
            "message": f"File '{filename}' deleted successfully",
            "chunks_deleted": len(chunk_ids_to_delete),
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
