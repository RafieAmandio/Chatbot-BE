from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime


class ChatMessage(BaseModel):
    role: str
    content: str
    metadata: Optional[Dict[str, Any]] = None


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 1000
    stream: Optional[bool] = True


class ChatResponse(BaseModel):
    conversation_id: str
    message: ChatMessage
    usage: Optional[Dict[str, Any]] = None


class ConversationCreate(BaseModel):
    title: Optional[str] = None


class ConversationResponse(BaseModel):
    id: str
    title: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    messages: List[ChatMessage] = []
    
    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    metadata: Optional[Dict[str, Any]]
    created_at: datetime
    
    class Config:
        from_attributes = True 