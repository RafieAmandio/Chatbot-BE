from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    tenant_domain: str


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    tenant_id: str
    is_admin: bool = False


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None


class PasswordReset(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str


class ChangePassword(BaseModel):
    current_password: str
    new_password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenData(BaseModel):
    user_id: Optional[str] = None


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: Optional[str]
    is_active: bool
    is_admin: bool
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


# Import here to avoid circular imports
from app.schemas.tenant import TenantResponse


class UserProfile(BaseModel):
    id: str
    email: str
    full_name: Optional[str]
    is_active: bool
    is_admin: bool
    tenant: TenantResponse
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True 