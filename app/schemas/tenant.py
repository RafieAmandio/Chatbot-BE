from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class TenantCreate(BaseModel):
    name: str
    domain: str
    description: Optional[str] = None
    max_users: Optional[int] = 100
    max_documents: Optional[int] = 1000
    max_products: Optional[int] = 1000


class TenantUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    max_users: Optional[int] = None
    max_documents: Optional[int] = None
    max_products: Optional[int] = None


class TenantResponse(BaseModel):
    id: str
    name: str
    domain: str
    description: Optional[str]
    is_active: bool
    created_at: datetime
    max_users: int
    max_documents: int
    max_products: int
    
    class Config:
        from_attributes = True 