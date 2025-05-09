from fastapi import APIRouter
from pydantic import BaseModel
from aiiris_backend.orchestrator.query_orchestrator import run_orchestration
from aiiris_backend.monitoring.metrics import api_requests_total

router = APIRouter()

class QueryRequest(BaseModel):
    query: str
    
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