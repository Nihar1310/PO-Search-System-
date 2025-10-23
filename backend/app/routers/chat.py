from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ..services import gpt_service
from ..database import get_db
from sqlalchemy.orm import Session
from .auth_local import get_current_user


router = APIRouter(prefix="/api", tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    structured_data: Optional[Dict[str, Any]] = None
    conversation_id: str


@router.post("/chat", response_model=ChatResponse)
def chat_endpoint(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    reply, structured, conversation_id = gpt_service.generate_reply(
        payload.message, payload.conversation_id, db
    )
    return {
        "response": reply,
        "structured_data": structured,
        "conversation_id": conversation_id,
    }
