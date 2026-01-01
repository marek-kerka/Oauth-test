from pydantic import BaseModel
from typing import Optional


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    user_email: str
    model: str = "mock-llm-v1"
