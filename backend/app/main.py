import sys
import asyncio
import os
from datetime import datetime

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from backend.app.router import router as query_router
from backend.shared.logger import get_logger
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from fastapi.staticfiles import StaticFiles
from backend.retrieval.retriever import load_vectorstore
from backend.shared.constants import VECTORSTORE_PATH_STR, FRONTEND_RENDERER_DIR, FRONTEND_ASSETS_DIR
from backend.core.tools.mcp import mcp_servers

logger = get_logger("MAIN")

# Fast API app start
app = FastAPI(
    title="AIris Yerel RAG API",
    version="0.1.0",
    description="Generative AI for Local Data",
)

logger.info("Starting AIris Backend API...")


@app.on_event("startup")
async def startup_event():
    """
    Uygulama başlangıcında vektör deposunu yükle ve MCP sunucularına bağlan.
    """
    try:
        for mcp_server in mcp_servers:
            try:
                await mcp_server.connect()
            except Exception as e:
                logger.error(f"Error connecting to MCP server: {e}")

        # Check if the vectorstore files exist, if not, we can't load it.
        # The user should upload files first.
        if os.path.exists(VECTORSTORE_PATH_STR):
            logger.info("Loading vectorstore...")
            load_vectorstore(VECTORSTORE_PATH_STR)
            logger.info("Vectorstore loaded successfully.")
        else:
            logger.warning("Vectorstore not found. Please upload files to create it.")

    except Exception as e:
        logger.error(f"Error during startup: {e}")
        # Depending on the desired behavior, you might want to raise the exception
        # to prevent the app from starting with a misconfigured state.
        # raise e


# UI statik dosyalarını sun
app.mount(
    "/static",
    StaticFiles(directory=str(FRONTEND_RENDERER_DIR)),
    name="static",
)
app.mount(
    "/assets", StaticFiles(directory=str(FRONTEND_ASSETS_DIR)), name="assets"
)

# expose_metrics()

# Geliştirme sırasında frontend bu api rahat erişmesi için
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def start_metrics_server():
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


@app.get("/metrics")
async def metrics():
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


@app.get("/health")
async def health_check():
    """
    Health check endpoint that returns JSON status
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "AIris Backend API",
        "version": "0.1.0",
    }


# API rotalarını bağla
app.include_router(query_router, prefix="/api")
