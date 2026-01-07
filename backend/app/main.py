import sys
import asyncio
import os
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.router import router as query_router
from backend.utils.market_data import init_market_data
from backend.shared.logger import get_logger
from fastapi.staticfiles import StaticFiles
from backend.retrieval.retriever import load_vectorstore, close_vectorstore
from backend.shared.constants import (
    VECTORSTORE_PATH_STR,
    FRONTEND_RENDERER_DIR,
    FRONTEND_ASSETS_DIR,
)

if sys.platform == "win32":
    # Use ProactorEventLoop for Windows subprocess support
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
logger = get_logger("MAIN")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan event handler for startup and shutdown.
    """
    # Startup
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

    except Exception as e:
        import traceback

        logger.error(f"Error loading vectorstore: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
    try:
        await init_market_data()
        logger.info("Market data initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing market data: {e}")
    try:
        from backend.core.checkpointer import setup_checkpointer

        checkpointer_success = await setup_checkpointer()
        if checkpointer_success:
            logger.info("✅ AsyncSqlite checkpointer initialized successfully")
        else:
            logger.warning(
                "AsyncSqlite checkpointer initialization failed. Agents will run without persistent state."
            )

    except Exception as e:
        logger.error(f"Error setting up checkpointer: {e}")
        logger.warning("Agents will run without persistent checkpointing")

    yield

    # Shutdown
    try:
        logger.info("Shutting down AIris Backend API...")
        from backend.core.checkpointer import close_checkpointer

        await close_checkpointer()
        close_vectorstore()
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


logger.info("Starting AIris Backend API...")

# Fast API app start
app = FastAPI(
    title="AIris Yerel RAG API",
    version="0.1.0",
    description="Generative AI for Local Data",
    lifespan=lifespan,
)


# Serve UI static files
app.mount(
    "/static",
    StaticFiles(directory=str(FRONTEND_RENDERER_DIR)),
    name="static",
)
app.mount("/assets", StaticFiles(directory=str(FRONTEND_ASSETS_DIR)), name="assets")

# expose_metrics()

# Allow frontend to easily access this API during development
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


# Connect API routes
app.include_router(query_router, prefix="/api")
