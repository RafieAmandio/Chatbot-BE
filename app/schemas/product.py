from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime


class ProductCreate(BaseModel):
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = None
    currency: Optional[str] = "USD"
    sku: Optional[str] = None
    stock_quantity: Optional[int] = 0
    specifications: Optional[Dict[str, Any]] = None
    meta_data: Optional[Dict[str, Any]] = None


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = None
    currency: Optional[str] = None
    sku: Optional[str] = None
    stock_quantity: Optional[int] = None
    specifications: Optional[Dict[str, Any]] = None
    meta_data: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class ProductResponse(BaseModel):
    id: str
    tenant_id: str
    name: str
    description: Optional[str]
    category: Optional[str]
    price: Optional[float]
    currency: Optional[str]
    sku: Optional[str]
    stock_quantity: Optional[int]
    specifications: Optional[Dict[str, Any]]
    meta_data: Optional[Dict[str, Any]]
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]
    vector_id: Optional[str]
    
    class Config:
        from_attributes = True


class ProductSearchRequest(BaseModel):
    query: str
    category: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    limit: Optional[int] = 10
    min_score: Optional[float] = 0.7


class ProductSearchResult(BaseModel):
    product: ProductResponse
    score: float 