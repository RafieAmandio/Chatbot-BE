from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import logging

from app.database.connection import get_db
from app.database.models import KnowledgeItem, User, Tenant
from app.schemas.knowledge import (
    KnowledgeItemCreate, KnowledgeItemUpdate, KnowledgeItemResponse,
    KnowledgeSearchRequest, KnowledgeSearchResult
)
from app.auth.dependencies import get_current_user, get_current_tenant
from app.services.vector_store import vector_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/knowledge", tags=["knowledge-management"])


@router.post("/", response_model=KnowledgeItemResponse)
async def create_knowledge_item(
    item_data: KnowledgeItemCreate,
    current_tenant: Tenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new knowledge item"""
    # Check tenant document limits
    item_count = db.query(KnowledgeItem).filter(
        KnowledgeItem.tenant_id == current_tenant.id
    ).count()
    if item_count >= current_tenant.max_documents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant has reached maximum document limit"
        )
    
    # Create knowledge item
    knowledge_item = KnowledgeItem(
        tenant_id=current_tenant.id,
        title=item_data.title,
        content=item_data.content,
        source=item_data.source,
        document_type=item_data.document_type,
        meta_data=item_data.meta_data
    )
    
    db.add(knowledge_item)
    db.commit()
    db.refresh(knowledge_item)
    
    # Add to vector store
    try:
        vector_id = await vector_store.add_knowledge_item(
            knowledge_item.id,
            knowledge_item.title,
            knowledge_item.content,
            current_tenant.id,
            metadata={
                "source": knowledge_item.source,
                "document_type": knowledge_item.document_type,
                **(knowledge_item.meta_data or {})
            }
        )
        
        # Update with vector ID
        knowledge_item.vector_id = vector_id
        db.commit()
        
    except Exception as e:
        logger.error(f"Error adding to vector store: {e}")
        # Don't fail the creation, just log the error
    
    logger.info(f"Knowledge item created: {knowledge_item.title} by {current_user.email}")
    return knowledge_item


@router.get("/", response_model=List[KnowledgeItemResponse])
async def list_knowledge_items(
    skip: int = 0,
    limit: int = 100,
    search: str = None,
    document_type: str = None,
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """List knowledge items for tenant"""
    query = db.query(KnowledgeItem).filter(
        KnowledgeItem.tenant_id == current_tenant.id,
        KnowledgeItem.is_active == True
    )
    
    if search:
        query = query.filter(
            KnowledgeItem.title.contains(search) | 
            KnowledgeItem.content.contains(search)
        )
    
    if document_type:
        query = query.filter(KnowledgeItem.document_type == document_type)
    
    items = query.offset(skip).limit(limit).all()
    return items


@router.get("/{item_id}", response_model=KnowledgeItemResponse)
async def get_knowledge_item(
    item_id: str,
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Get specific knowledge item"""
    item = db.query(KnowledgeItem).filter(
        KnowledgeItem.id == item_id,
        KnowledgeItem.tenant_id == current_tenant.id
    ).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Knowledge item not found")
    
    return item


@router.put("/{item_id}", response_model=KnowledgeItemResponse)
async def update_knowledge_item(
    item_id: str,
    item_data: KnowledgeItemUpdate,
    current_tenant: Tenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update knowledge item"""
    item = db.query(KnowledgeItem).filter(
        KnowledgeItem.id == item_id,
        KnowledgeItem.tenant_id == current_tenant.id
    ).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Knowledge item not found")
    
    # Update fields
    update_data = item_data.dict(exclude_unset=True)
    content_changed = False
    
    for field, value in update_data.items():
        if field in ["title", "content"] and getattr(item, field) != value:
            content_changed = True
        setattr(item, field, value)
    
    db.commit()
    db.refresh(item)
    
    # Update vector store if content changed
    if content_changed and item.vector_id:
        try:
            await vector_store.update_knowledge_item(
                item.vector_id,
                item.title,
                item.content,
                current_tenant.id,
                metadata={
                    "source": item.source,
                    "document_type": item.document_type,
                    **(item.meta_data or {})
                }
            )
        except Exception as e:
            logger.error(f"Error updating vector store: {e}")
    
    logger.info(f"Knowledge item updated: {item.title} by {current_user.email}")
    return item


@router.delete("/{item_id}")
async def delete_knowledge_item(
    item_id: str,
    current_tenant: Tenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete knowledge item"""
    item = db.query(KnowledgeItem).filter(
        KnowledgeItem.id == item_id,
        KnowledgeItem.tenant_id == current_tenant.id
    ).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Knowledge item not found")
    
    # Remove from vector store
    if item.vector_id:
        try:
            await vector_store.delete_knowledge_item(item.vector_id, current_tenant.id)
        except Exception as e:
            logger.error(f"Error removing from vector store: {e}")
    
    # Soft delete
    item.is_active = False
    db.commit()
    
    logger.info(f"Knowledge item deleted: {item.title} by {current_user.email}")
    return {"message": "Knowledge item deleted successfully"}


@router.post("/search", response_model=List[KnowledgeSearchResult])
async def search_knowledge(
    search_request: KnowledgeSearchRequest,
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Search knowledge items using vector similarity"""
    try:
        # Search in vector store
        results = await vector_store.search_knowledge(
            query=search_request.query,
            tenant_id=current_tenant.id,
            limit=search_request.limit,
            min_score=search_request.min_score
        )
        
        # Get knowledge items from database
        search_results = []
        for result in results:
            item = db.query(KnowledgeItem).filter(
                KnowledgeItem.id == result["id"],
                KnowledgeItem.tenant_id == current_tenant.id,
                KnowledgeItem.is_active == True
            ).first()
            
            if item:
                search_results.append(KnowledgeSearchResult(
                    item=item,
                    score=result["score"]
                ))
        
        return search_results
        
    except Exception as e:
        logger.error(f"Error searching knowledge: {e}")
        raise HTTPException(status_code=500, detail="Search failed")


@router.get("/types/list")
async def list_document_types(
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """List all document types in tenant"""
    types = db.query(KnowledgeItem.document_type).filter(
        KnowledgeItem.tenant_id == current_tenant.id,
        KnowledgeItem.is_active == True,
        KnowledgeItem.document_type.isnot(None)
    ).distinct().all()
    
    return [t[0] for t in types if t[0]] 