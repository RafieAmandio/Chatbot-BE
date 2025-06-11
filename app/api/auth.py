from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from typing import Optional
import logging

from app.database.connection import get_db
from app.database.models import User, Tenant
from app.schemas.auth import (
    UserLogin, UserRegister, UserCreate, UserUpdate, PasswordReset, 
    PasswordResetConfirm, ChangePassword, Token, UserResponse, UserProfile
)
from app.services.auth_service import auth_service
from app.auth.dependencies import get_current_user, get_current_tenant, get_admin_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer()


@router.post("/login", response_model=Token)
async def login(
    user_credentials: UserLogin,
    db: Session = Depends(get_db)
):
    """Authenticate user and return access token"""
    try:
        # Authenticate user
        user = auth_service.authenticate_user(
            db=db,
            email=user_credentials.email,
            password=user_credentials.password
        )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Create access token
        access_token_expires = timedelta(minutes=auth_service.access_token_expire_minutes)
        access_token = auth_service.create_access_token(
            data={"sub": user.id},
            expires_delta=access_token_expires
        )
        
        logger.info(f"User {user.email} logged in successfully")
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": auth_service.access_token_expire_minutes * 60
        }
        
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.post("/register", response_model=UserResponse)
async def register(
    user_data: UserRegister,
    db: Session = Depends(get_db)
):
    """Register a new user"""
    try:
        # Check if tenant exists
        tenant = auth_service.check_tenant_domain(db, user_data.tenant_domain)
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found or inactive"
            )
        
        # Check if email is available
        if not auth_service.is_email_available(db, user_data.email, tenant.id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Create user
        user = auth_service.create_user(
            db=db,
            email=user_data.email,
            password=user_data.password,
            full_name=user_data.full_name,
            tenant_id=tenant.id,
            is_admin=False
        )
        
        logger.info(f"User {user.email} registered successfully")
        return user
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.get("/me", response_model=UserProfile)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
    current_tenant: Tenant = Depends(get_current_tenant)
):
    """Get current user profile"""
    return UserProfile(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        is_admin=current_user.is_admin,
        tenant={
            "id": current_tenant.id,
            "name": current_tenant.name,
            "domain": current_tenant.domain,
            "description": current_tenant.description,
            "is_active": current_tenant.is_active,
            "created_at": current_tenant.created_at
        },
        created_at=current_user.created_at,
        updated_at=current_user.updated_at
    )


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update current user profile"""
    try:
        # Update user fields
        if user_update.email is not None:
            # Check if new email is available
            if user_update.email != current_user.email:
                if not auth_service.is_email_available(db, user_update.email, current_user.tenant_id):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Email already in use"
                    )
                current_user.email = user_update.email
        
        if user_update.full_name is not None:
            current_user.full_name = user_update.full_name
        
        # Only admins can change admin status and active status
        if user_update.is_admin is not None and current_user.is_admin:
            current_user.is_admin = user_update.is_admin
        
        if user_update.is_active is not None and current_user.is_admin:
            current_user.is_active = user_update.is_active
        
        db.commit()
        db.refresh(current_user)
        
        logger.info(f"User {current_user.email} updated profile")
        return current_user
        
    except Exception as e:
        logger.error(f"Profile update error: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Profile update failed"
        )


@router.post("/change-password")
async def change_password(
    password_data: ChangePassword,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change user password"""
    try:
        # Verify current password
        if not auth_service.verify_password(password_data.current_password, current_user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incorrect current password"
            )
        
        # Update password
        auth_service.update_user_password(db, current_user, password_data.new_password)
        
        logger.info(f"User {current_user.email} changed password")
        return {"message": "Password updated successfully"}
        
    except Exception as e:
        logger.error(f"Password change error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password change failed"
        )


@router.post("/password-reset")
async def request_password_reset(
    reset_data: PasswordReset,
    db: Session = Depends(get_db)
):
    """Request password reset"""
    try:
        # Find user by email
        user = auth_service.get_user_by_email(db, reset_data.email)
        
        if not user:
            # Don't reveal if email exists
            return {"message": "If the email exists, a reset link has been sent"}
        
        # Create reset token
        reset_token = auth_service.create_reset_token(user.id)
        
        # TODO: Send email with reset token
        # For now, we'll just log it
        logger.info(f"Password reset requested for {user.email}. Reset token: {reset_token}")
        
        return {"message": "If the email exists, a reset link has been sent"}
        
    except Exception as e:
        logger.error(f"Password reset request error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password reset request failed"
        )


@router.post("/password-reset/confirm")
async def confirm_password_reset(
    reset_data: PasswordResetConfirm,
    db: Session = Depends(get_db)
):
    """Confirm password reset with token"""
    try:
        # Verify reset token
        user_id = auth_service.verify_reset_token(reset_data.token)
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token"
            )
        
        # Get user
        user = auth_service.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Update password
        auth_service.update_user_password(db, user, reset_data.new_password)
        
        logger.info(f"Password reset completed for {user.email}")
        return {"message": "Password reset successfully"}
        
    except Exception as e:
        logger.error(f"Password reset confirmation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password reset failed"
        )


@router.post("/users", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Create a new user (Admin only)"""
    try:
        # Check if email is available
        if not auth_service.is_email_available(db, user_data.email, user_data.tenant_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Create user
        user = auth_service.create_user(
            db=db,
            email=user_data.email,
            password=user_data.password,
            full_name=user_data.full_name,
            tenant_id=user_data.tenant_id,
            is_admin=user_data.is_admin
        )
        
        logger.info(f"Admin {current_user.email} created user {user.email}")
        return user
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"User creation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User creation failed"
        )


@router.get("/verify-token")
async def verify_token(current_user: User = Depends(get_current_user)):
    """Verify if current token is valid"""
    return {
        "valid": True,
        "user_id": current_user.id,
        "email": current_user.email
    } 