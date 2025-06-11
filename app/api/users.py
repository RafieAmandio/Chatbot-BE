from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import logging

from app.database.connection import get_db
from app.database.models import User, Tenant
from app.schemas.auth import UserCreate, UserUpdate, UserResponse
from app.auth.dependencies import get_current_user, get_current_tenant, get_admin_user
from app.services.auth_service import auth_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["user-management"])


@router.post("/", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new user within tenant"""
    # Check if user has permission to create users
    if not current_user.is_admin and current_user.tenant_id != user_data.tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Check if tenant exists
    tenant = db.query(Tenant).filter(Tenant.id == user_data.tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    # Check if email already exists in tenant
    existing_user = db.query(User).filter(
        User.email == user_data.email,
        User.tenant_id == user_data.tenant_id
    ).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists in tenant"
        )
    
    # Check tenant user limits
    user_count = db.query(User).filter(User.tenant_id == user_data.tenant_id).count()
    if user_count >= tenant.max_users:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant has reached maximum user limit"
        )
    
    # Hash password and create user
    hashed_password = auth_service.get_password_hash(user_data.password)
    
    user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        tenant_id=user_data.tenant_id,
        is_admin=user_data.is_admin
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    logger.info(f"User created: {user.email} in tenant {user_data.tenant_id} by {current_user.email}")
    return user


@router.get("/", response_model=List[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    tenant_id: str = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List users"""
    query = db.query(User)
    
    if current_user.is_admin:
        # Super admin can see all users
        if tenant_id:
            query = query.filter(User.tenant_id == tenant_id)
    else:
        # Regular users can only see users in their tenant
        query = query.filter(User.tenant_id == current_user.tenant_id)
    
    users = query.offset(skip).limit(limit).all()
    return users


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user details"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Users can only view users in their tenant or themselves, unless they're super admin
    if not current_user.is_admin and current_user.tenant_id != user.tenant_id and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return user


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Users can only update themselves or users in their tenant if admin
    if not current_user.is_admin and current_user.tenant_id != user.tenant_id and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Regular users can't modify admin status
    if not current_user.is_admin and user_data.is_admin is not None:
        raise HTTPException(status_code=403, detail="Cannot modify admin status")
    
    # Update fields
    update_data = user_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    
    db.commit()
    db.refresh(user)
    
    logger.info(f"User updated: {user.email} by {current_user.email}")
    return user


@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete/deactivate user"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Only admin can delete users, and they must be in same tenant
    if not current_user.is_admin and current_user.tenant_id != user.tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Prevent self-deletion
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    
    # Soft delete - just deactivate
    user.is_active = False
    db.commit()
    
    logger.info(f"User deactivated: {user.email} by {current_user.email}")
    return {"message": "User deactivated successfully"}


@router.post("/{user_id}/activate")
async def activate_user(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Reactivate user"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Only admin can activate users
    if not current_user.is_admin and current_user.tenant_id != user.tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    user.is_active = True
    db.commit()
    
    logger.info(f"User activated: {user.email} by {current_user.email}")
    return {"message": "User activated successfully"} 