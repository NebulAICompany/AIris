from fastapi import APIRouter
from pydantic import BaseModel
from aiiris_backend.orchestrator.query_orchestrator import run_orchestration

router = APIRouter()

class QueryRequest(BaseModel):
    query: str
    
@router.post("/query")
def handle_query(request: QueryRequest):
    """
    Kullanıcının gönderdiği sorguyu alır,
    orchestrator üzerinden işler ve LLM yanıtını döner.
    """
    query = request.query
    answer = run_orchestration(query)
    return {"response": answer}