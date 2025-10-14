from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Optional

class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class ChatMessage(BaseModel):
    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class ChatRequest(BaseModel):
    message: str  

class ChatResponse(BaseModel):
    message: ChatMessage
    context_documents: List[str] = []
    status: str = "success"
