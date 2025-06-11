from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional
import logging

from app.config import settings
from app.database.connection import get_db
from app.database.models import User, Tenant
from app.services.auth_service import auth_service

logger = logging.getLogger(__name__)

security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """FastAPI dependency to get current authenticated user"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Verify token using auth service
    token_data = auth_service.verify_token(credentials.credentials)
    if not token_data:
        raise credentials_exception
    
    # Get user from database
    user = auth_service.get_user_by_id(db, token_data.user_id)
    if not user:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user"
        )
    
    return user


def get_current_tenant(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Tenant:
    """FastAPI dependency to get current tenant"""
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    if not tenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant is inactive"
        )
    
    return tenant


def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """FastAPI dependency to ensure current user is admin"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


def get_tenant_from_domain(
    x_tenant_domain: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> Optional[Tenant]:
    """Get tenant from domain header (for public endpoints)"""
    if not x_tenant_domain:
        return None
    
    tenant = db.query(Tenant).filter(
        Tenant.domain == x_tenant_domain,
        Tenant.is_active == True
    ).first()
    
    return tenant


def get_current_user_from_token(token: str, db: Session) -> User:
    """Get current user from JWT token (helper function for internal use)"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Verify token using auth service
    token_data = auth_service.verify_token(token)
    if not token_data:
        raise credentials_exception
    
    # Get user from database
    user = auth_service.get_user_by_id(db, token_data.user_id)
    if not user:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user"
        )
    
    return user 