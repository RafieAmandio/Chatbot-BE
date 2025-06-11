from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime


class PromptCreate(BaseModel):
    name: str
    system_prompt: str
    description: Optional[str] = None
    is_default: Optional[bool] = False
    variables: Optional[Dict[str, Any]] = None


class PromptUpdate(BaseModel):
    name: Optional[str] = None
    system_prompt: Optional[str] = None
    description: Optional[str] = None
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None
    variables: Optional[Dict[str, Any]] = None


class PromptResponse(BaseModel):
    id: str
    tenant_id: str
    name: str
    system_prompt: str
    description: Optional[str]
    is_default: bool
    is_active: bool
    variables: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class PromptTestRequest(BaseModel):
    system_prompt: str
    test_message: str
    variables: Optional[Dict[str, Any]] = None


class PromptTestResponse(BaseModel):
    rendered_prompt: str
    test_response: str
    usage: Optional[Dict[str, Any]] = None 