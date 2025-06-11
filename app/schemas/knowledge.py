from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime


class KnowledgeItemCreate(BaseModel):
    title: str
    content: str
    source: Optional[str] = None
    document_type: Optional[str] = None
    meta_data: Optional[Dict[str, Any]] = None


class KnowledgeItemUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    source: Optional[str] = None
    document_type: Optional[str] = None
    meta_data: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class KnowledgeItemResponse(BaseModel):
    id: str
    tenant_id: str
    title: str
    content: str
    source: Optional[str]
    document_type: Optional[str]
    meta_data: Optional[Dict[str, Any]]
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]
    vector_id: Optional[str]
    
    class Config:
        from_attributes = True


class KnowledgeSearchRequest(BaseModel):
    query: str
    limit: Optional[int] = 10
    min_score: Optional[float] = 0.7


class KnowledgeSearchResult(BaseModel):
    item: KnowledgeItemResponse
    score: float 