import sys
import asyncio
import os
from datetime import datetime

if sys.platform == "win32":
    # Use ProactorEventLoop for Windows subprocess support
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from backend.app.router import router as query_router
from backend.shared.logger import get_logger

from fastapi.staticfiles import StaticFiles
from backend.retrieval.retriever import load_vectorstore
from backend.shared.constants import (
    VECTORSTORE_PATH_STR,
    FRONTEND_RENDERER_DIR,
    FRONTEND_ASSETS_DIR,
)


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
        if not os.path.exists(VECTORSTORE_PATH_STR):
            os.makedirs(VECTORSTORE_PATH_STR)
            logger.info(f"Vectorstore directory created at: {VECTORSTORE_PATH_STR}")

        # Check if the vectorstore files exist, if not, we can't load it.
        # The user should upload files first.
        if os.path.exists(VECTORSTORE_PATH_STR):
            logger.info("Loading vectorstore...")
            load_vectorstore(VECTORSTORE_PATH_STR)
            logger.info("Vectorstore loaded successfully.")
        else:
            logger.warning("Vectorstore not found. Please upload files to create it.")

        # Connect MCP servers using best practices
        logger.info("Connecting MCP servers...")
        from backend.core.tools.mcp import connect_mcp_servers

        await connect_mcp_servers()
        logger.info("MCP servers connected successfully.")

    except Exception as e:
        import traceback

        logger.error(f"Error during startup: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        # Depending on the desired behavior, you might want to raise the exception
        # to prevent the app from starting with a misconfigured state.
        # raise e


@app.on_event("shutdown")
async def shutdown_event():
    """
    Uygulama kapanırken MCP sunucularından bağlantıyı kes.
    """
    try:
        logger.info("Disconnecting MCP servers...")
        from backend.core.tools.mcp import disconnect_mcp_servers

        await disconnect_mcp_servers()
        logger.info("MCP servers disconnected successfully.")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


# UI statik dosyalarını sun
app.mount(
    "/static",
    StaticFiles(directory=str(FRONTEND_RENDERER_DIR)),
    name="static",
)
app.mount("/assets", StaticFiles(directory=str(FRONTEND_ASSETS_DIR)), name="assets")

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
async def root():
    return {"message": "AIris Backend API", "version": "0.1.0", "status": "running"}


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
