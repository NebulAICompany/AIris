from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from aiiris_backend.app.router import router as query_router
from aiiris_backend.monitoring.metrics import expose_metrics
from aiiris_backend.libs.logger import setup_logging, get_logger
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

# Initialize logging first
setup_logging()
logger = get_logger(__name__)

# Fast API app start
app = FastAPI(
    title="AIris Yerel RAG API",
    version="0.1.0",
    description="Generative AI for Local Data",
)

logger.info("Starting AIris Backend API...")

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

# Bu dosya doğrudan çalıştırılırsa sunucu başlasın
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("aiiris_backend.app.main:app", host="127.0.0.1", port=8000, reload=True)
   