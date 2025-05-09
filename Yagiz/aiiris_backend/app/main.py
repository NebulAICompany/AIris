from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from aiiris_backend.app.router import router as query_router
from aiiris_backend.monitoring.metrics import expose_metrics

# Fast API app start
app = FastAPI(
    title="AIris Yerel RAG API",
    version="0.1.0",
    description="Generative AI for Local Data",
)
expose_metrics(port=9090)
# Geliştirme sırasında frontend bu api rahat erişmesi için
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API rotalarını bağla
app.include_router(query_router, prefix="/api")

# Bu dosya doğrudan çalıştırılırsa sunucu başlasın
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("aiiris_backend.app.main:app", host="127.0.0.1", port=8000, reload=True)
   