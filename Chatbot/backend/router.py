from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from .assistant import LuviaAssistant

router = APIRouter(prefix="/api/chatbot", tags=["LUVIA Chatbot"])
assistant = LuviaAssistant()
class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1500)
    session_id: str = Field(default="default", max_length=100)
@router.get("/health")
def health(): return {"status": "ok", "service": "LUVIA Chatbot"}
@router.post("/chat")
def chat(payload: ChatRequest):
    try: return assistant.reply(payload.message.strip(), payload.session_id)
    except Exception as exc: raise HTTPException(status_code=500, detail=f"Chatbot error: {exc}")
