import sys
import asyncio
import os

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from aiiris_backend.app.router import router as query_router
from aiiris_backend.monitoring.metrics import expose_metrics
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from fastapi.staticfiles import StaticFiles
from aiiris_backend.retrieval.retriever import load_vectorstore

# Proje ana dizinini belirle
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VECTORSTORE_PATH = os.path.join(BASE_DIR, "vectorstore")

# Fast API app start
app = FastAPI(
    title="AIris Yerel RAG API",
    version="0.1.0",
    description="Generative AI for Local Data",
)


@app.on_event("startup")
async def startup_event():
    """
    Uygulama başlangıcında vektör deposunu yükle.
    """
    try:
        if not os.path.exists(VECTORSTORE_PATH):
            os.makedirs(VECTORSTORE_PATH)
            print(f"Vectorstore directory created at: {VECTORSTORE_PATH}")

        # Check if the vectorstore files exist, if not, we can't load it.
        # The user should upload files first.
        faiss_path = os.path.join(VECTORSTORE_PATH, "index.faiss")
        if os.path.exists(faiss_path):
            print("Loading vectorstore...")
            load_vectorstore(VECTORSTORE_PATH)
            print("Vectorstore loaded successfully.")
        else:
            print("Vectorstore not found. Please upload files to create it.")

    except Exception as e:
        print(f"Error during startup: {e}")
        # Depending on the desired behavior, you might want to raise the exception
        # to prevent the app from starting with a misconfigured state.
        # raise e


# UI statik dosyalarını sun
ui_path = os.path.join(os.path.dirname(__file__), "..", "..", "aiiris_ui")
app.mount(
    "/static",
    StaticFiles(directory=os.path.join(ui_path, "src", "renderer")),
    name="static",
)
app.mount(
    "/assets", StaticFiles(directory=os.path.join(ui_path, "assets")), name="assets"
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


# API rotalarını bağla
app.include_router(query_router, prefix="/api")
