from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import logging

from app.database.connection import get_db
from app.database.models import Tenant, User
from app.schemas.tenant import TenantCreate, TenantUpdate, TenantResponse
from app.auth.dependencies import get_current_user, get_admin_user
from app.services.auth_service import auth_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tenants", tags=["tenant-management"])


@router.post("/", response_model=TenantResponse)
async def create_tenant(
    tenant_data: TenantCreate,
    current_user: User = Depends(get_admin_user),  # Only super admin can create tenants
    db: Session = Depends(get_db)
):
    """Create a new tenant"""
    # Check if domain already exists
    existing_tenant = db.query(Tenant).filter(Tenant.domain == tenant_data.domain).first()
    if existing_tenant:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant with this domain already exists"
        )
    
    # Create tenant
    tenant = Tenant(
        name=tenant_data.name,
        domain=tenant_data.domain,
        description=tenant_data.description,
        max_users=tenant_data.max_users,
        max_documents=tenant_data.max_documents,
        max_products=tenant_data.max_products
    )
    
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    
    logger.info(f"Tenant created: {tenant.domain} by user {current_user.email}")
    return tenant


@router.get("/", response_model=List[TenantResponse])
async def list_tenants(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_admin_user),  # Only super admin can list all tenants
    db: Session = Depends(get_db)
):
    """List all tenants (admin only)"""
    tenants = db.query(Tenant).offset(skip).limit(limit).all()
    return tenants


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get tenant details"""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    # Users can only view their own tenant, unless they're super admin
    if not current_user.is_admin and current_user.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return tenant


@router.put("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: str,
    tenant_data: TenantUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update tenant settings"""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    # Only super admin or tenant admin can update
    if not current_user.is_admin and current_user.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Update fields
    update_data = tenant_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(tenant, field, value)
    
    db.commit()
    db.refresh(tenant)
    
    logger.info(f"Tenant updated: {tenant.domain} by user {current_user.email}")
    return tenant


@router.delete("/{tenant_id}")
async def delete_tenant(
    tenant_id: str,
    current_user: User = Depends(get_admin_user),  # Only super admin can delete
    db: Session = Depends(get_db)
):
    """Delete/deactivate tenant"""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    # Soft delete - just deactivate
    tenant.is_active = False
    db.commit()
    
    logger.info(f"Tenant deactivated: {tenant.domain} by user {current_user.email}")
    return {"message": "Tenant deactivated successfully"}


@router.get("/{tenant_id}/stats")
async def get_tenant_stats(
    tenant_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get tenant statistics"""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    # Users can only view their own tenant stats, unless they're super admin
    if not current_user.is_admin and current_user.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Count related entities
    from app.database.models import User, KnowledgeItem, Product, Conversation
    
    user_count = db.query(User).filter(User.tenant_id == tenant_id).count()
    knowledge_count = db.query(KnowledgeItem).filter(KnowledgeItem.tenant_id == tenant_id).count()
    product_count = db.query(Product).filter(Product.tenant_id == tenant_id).count()
    conversation_count = db.query(Conversation).filter(Conversation.tenant_id == tenant_id).count()
    
    return {
        "tenant_id": tenant_id,
        "users": user_count,
        "knowledge_items": knowledge_count,
        "products": product_count,
        "conversations": conversation_count,
        "limits": {
            "max_users": tenant.max_users,
            "max_documents": tenant.max_documents,
            "max_products": tenant.max_products
        }
    } 