import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.models import User, Tenant, UploadedFile, KnowledgeItem, Product
from app.schemas.admin import (
    AdminDashboard, SystemOverview, TenantAnalytics, UserAnalytics,
    KnowledgeAnalytics, FileSystemAnalytics, ChatAnalytics, SystemHealth,
    AnalyticsRequest, TimeRange, TenantAction, UserAction, SystemAction,
    BatchActionResult, SystemConfiguration, TenantConfiguration,
    ActivityLogsResponse, LogsRequest, TenantUsageMetrics, UserActivityMetric
)
from app.auth.admin_middleware import require_admin, require_super_admin
from app.services.admin_service import admin_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin-dashboard"])


# Dashboard Overview
@router.get("/dashboard", response_model=AdminDashboard)
async def get_admin_dashboard(
    time_range: TimeRange = Query(TimeRange.DAY, description="Time range for analytics"),
    tenant_id: Optional[str] = Query(None, description="Specific tenant ID (super admin only)"),
    include_details: bool = Query(False, description="Include detailed breakdowns"),
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get comprehensive admin dashboard data"""
    try:
        # Check if requesting data for specific tenant (super admin only)
        if tenant_id and admin_user.tenant_id != tenant_id:
            # Verify super admin access
            tenant = db.query(Tenant).filter(Tenant.id == admin_user.tenant_id).first()
            if not tenant or tenant.domain != "default":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied for cross-tenant data"
                )
        
        dashboard = await admin_service.get_admin_dashboard(db, time_range)
        logger.info(f"Dashboard accessed by {admin_user.email}")
        return dashboard
        
    except Exception as e:
        logger.error(f"Error getting admin dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# System Overview
@router.get("/overview", response_model=SystemOverview)
async def get_system_overview(
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get system overview metrics"""
    try:
        overview = await admin_service.get_system_overview(db)
        return overview
    except Exception as e:
        logger.error(f"Error getting system overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Analytics Endpoints
@router.get("/analytics/tenants", response_model=TenantAnalytics)
async def get_tenant_analytics(
    time_range: TimeRange = Query(TimeRange.DAY),
    admin_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """Get tenant usage analytics (super admin only)"""
    try:
        analytics = await admin_service.get_tenant_analytics(db, time_range)
        return analytics
    except Exception as e:
        logger.error(f"Error getting tenant analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/users", response_model=UserAnalytics)
async def get_user_analytics(
    time_range: TimeRange = Query(TimeRange.DAY),
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get user activity analytics"""
    try:
        analytics = await admin_service.get_user_analytics(db, time_range)
        return analytics
    except Exception as e:
        logger.error(f"Error getting user analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/knowledge", response_model=KnowledgeAnalytics)
async def get_knowledge_analytics(
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get knowledge base analytics"""
    try:
        analytics = await admin_service.get_knowledge_analytics(db)
        return analytics
    except Exception as e:
        logger.error(f"Error getting knowledge analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/files", response_model=FileSystemAnalytics)
async def get_file_analytics(
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get file system analytics"""
    try:
        analytics = await admin_service.get_file_analytics(db)
        return analytics
    except Exception as e:
        logger.error(f"Error getting file analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/chat", response_model=ChatAnalytics)
async def get_chat_analytics(
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get chat and conversation analytics"""
    try:
        analytics = await admin_service.get_chat_analytics(db)
        return analytics
    except Exception as e:
        logger.error(f"Error getting chat analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# System Health
@router.get("/health", response_model=SystemHealth)
async def get_system_health(
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get comprehensive system health status"""
    try:
        health = await admin_service.get_system_health(db)
        return health
    except Exception as e:
        logger.error(f"Error getting system health: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Tenant Management
@router.get("/tenants", response_model=List[TenantUsageMetrics])
async def list_tenants_with_usage(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    admin_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """List all tenants with usage metrics (super admin only)"""
    try:
        tenants = db.query(Tenant).filter(Tenant.is_active == True).offset(skip).limit(limit).all()
        
        tenant_metrics = []
        for tenant in tenants:
            metrics = await admin_service._get_tenant_usage_metrics(db, tenant.id)
            tenant_metrics.append(metrics)
        
        return tenant_metrics
    except Exception as e:
        logger.error(f"Error listing tenants: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tenants/actions", response_model=BatchActionResult)
async def execute_tenant_action(
    action: TenantAction,
    admin_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """Execute administrative action on tenant (super admin only)"""
    try:
        tenant = db.query(Tenant).filter(Tenant.id == action.tenant_id).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")
        
        success = False
        error_message = ""
        
        if action.action == "activate":
            tenant.is_active = True
            success = True
        elif action.action == "deactivate":
            tenant.is_active = False
            success = True
        elif action.action == "upgrade":
            # Handle tenant upgrade logic
            if action.parameters:
                for key, value in action.parameters.items():
                    if hasattr(tenant, key):
                        setattr(tenant, key, value)
            success = True
        else:
            error_message = f"Unknown action: {action.action}"
        
        if success:
            db.commit()
            logger.info(f"Tenant action '{action.action}' executed on {tenant.name} by {admin_user.email}")
        
        return BatchActionResult(
            action=action.action,
            total_items=1,
            successful=1 if success else 0,
            failed=0 if success else 1,
            errors=[error_message] if error_message else [],
            execution_time=0.1
        )
        
    except Exception as e:
        logger.error(f"Error executing tenant action: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# User Management
@router.get("/users", response_model=List[UserActivityMetric])
async def list_users_with_activity(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    tenant_id: Optional[str] = Query(None),
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """List users with activity metrics"""
    try:
        # Check permissions for cross-tenant access
        if tenant_id and tenant_id != admin_user.tenant_id:
            tenant = db.query(Tenant).filter(Tenant.id == admin_user.tenant_id).first()
            if not tenant or tenant.domain != "default":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied for cross-tenant data"
                )
        
        # Build query
        query = db.query(User).filter(User.is_active == True)
        
        if tenant_id:
            query = query.filter(User.tenant_id == tenant_id)
        elif admin_user.tenant_id != tenant_id:
            # Non-super admin can only see their own tenant
            tenant = db.query(Tenant).filter(Tenant.id == admin_user.tenant_id).first()
            if tenant and tenant.domain != "default":
                query = query.filter(User.tenant_id == admin_user.tenant_id)
        
        users = query.offset(skip).limit(limit).all()
        
        user_metrics = []
        for user in users:
            tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
            
            # Get user activity stats
            from sqlalchemy import func
            from app.database.models import Conversation, Message
            
            conv_count = db.query(func.count(Conversation.id)).filter(
                Conversation.user_id == user.id
            ).scalar() or 0
            
            msg_count = db.query(func.count(Message.id)).join(Conversation).filter(
                Conversation.user_id == user.id
            ).scalar() or 0
            
            last_activity = db.query(func.max(Conversation.updated_at)).filter(
                Conversation.user_id == user.id
            ).scalar()
            
            user_metrics.append(UserActivityMetric(
                user_id=user.id,
                email=user.email,
                full_name=user.full_name,
                tenant_name=tenant.name if tenant else "Unknown",
                total_conversations=conv_count,
                total_messages=msg_count,
                last_activity=last_activity,
                signup_date=user.created_at,
                is_active=user.is_active
            ))
        
        return user_metrics
        
    except Exception as e:
        logger.error(f"Error listing users: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/users/actions", response_model=BatchActionResult)
async def execute_user_action(
    action: UserAction,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Execute administrative action on user"""
    try:
        user = db.query(User).filter(User.id == action.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check permissions
        if user.tenant_id != admin_user.tenant_id:
            tenant = db.query(Tenant).filter(Tenant.id == admin_user.tenant_id).first()
            if not tenant or tenant.domain != "default":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied for cross-tenant user"
                )
        
        success = False
        error_message = ""
        
        if action.action == "activate":
            user.is_active = True
            success = True
        elif action.action == "deactivate":
            user.is_active = False
            success = True
        elif action.action == "change_role":
            if action.parameters and "is_admin" in action.parameters:
                user.is_admin = action.parameters["is_admin"]
                success = True
        elif action.action == "reset_password":
            # Would implement password reset logic
            success = True
        else:
            error_message = f"Unknown action: {action.action}"
        
        if success:
            db.commit()
            logger.info(f"User action '{action.action}' executed on {user.email} by {admin_user.email}")
        
        return BatchActionResult(
            action=action.action,
            total_items=1,
            successful=1 if success else 0,
            failed=0 if success else 1,
            errors=[error_message] if error_message else [],
            execution_time=0.1
        )
        
    except Exception as e:
        logger.error(f"Error executing user action: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# System Configuration
@router.get("/config/system")
async def get_system_configuration(
    admin_user: User = Depends(require_super_admin)
):
    """Get system configuration (super admin only)"""
    from app.config import settings
    
    return {
        "maintenance_mode": False,
        "registration_enabled": True,
        "file_upload_enabled": True,
        "max_file_size": 50 * 1024 * 1024,  # 50MB
        "supported_file_types": ["pdf", "docx", "txt", "csv", "xlsx", "html", "json", "xml"],
        "app_version": settings.app_version,
        "debug_mode": settings.debug
    }


@router.put("/config/system")
async def update_system_configuration(
    config_update: Dict[str, Any],
    admin_user: User = Depends(require_super_admin)
):
    """Update system configuration (super admin only)"""
    # This would update system-wide settings
    # For now, return success
    logger.info(f"System configuration updated by {admin_user.email}: {config_update}")
    return {"message": "Configuration updated successfully"}


# System Actions
@router.post("/actions/system", response_model=BatchActionResult)
async def execute_system_action(
    action: SystemAction,
    background_tasks: BackgroundTasks,
    admin_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """Execute system-wide administrative action (super admin only)"""
    try:
        success = False
        error_message = ""
        
        if action.action == "maintenance":
            # Toggle maintenance mode
            success = True
            logger.info(f"Maintenance mode toggled by {admin_user.email}")
        elif action.action == "backup":
            # Trigger database backup
            # background_tasks.add_task(perform_backup)
            success = True
            logger.info(f"Backup initiated by {admin_user.email}")
        elif action.action == "cleanup":
            # Cleanup old files, logs, etc.
            # background_tasks.add_task(perform_cleanup)
            success = True
            logger.info(f"Cleanup initiated by {admin_user.email}")
        else:
            error_message = f"Unknown action: {action.action}"
        
        return BatchActionResult(
            action=action.action,
            total_items=1,
            successful=1 if success else 0,
            failed=0 if success else 1,
            errors=[error_message] if error_message else [],
            execution_time=0.1
        )
        
    except Exception as e:
        logger.error(f"Error executing system action: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Data Export
@router.get("/export/tenant-data/{tenant_id}")
async def export_tenant_data(
    tenant_id: str,
    admin_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """Export all data for a specific tenant (super admin only)"""
    try:
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")
        
        # Collect all tenant data
        export_data = {
            "tenant": {
                "id": tenant.id,
                "name": tenant.name,
                "domain": tenant.domain,
                "created_at": tenant.created_at.isoformat()
            },
            "users_count": db.query(User).filter(User.tenant_id == tenant_id).count(),
            "conversations_count": db.query(Conversation).filter(Conversation.tenant_id == tenant_id).count(),
            "knowledge_items_count": db.query(KnowledgeItem).filter(KnowledgeItem.tenant_id == tenant_id).count(),
            "products_count": db.query(Product).filter(Product.tenant_id == tenant_id).count(),
            "files_count": db.query(UploadedFile).filter(UploadedFile.tenant_id == tenant_id).count()
        }
        
        logger.info(f"Tenant data exported for {tenant.name} by {admin_user.email}")
        return export_data
        
    except Exception as e:
        logger.error(f"Error exporting tenant data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Activity Logs (placeholder - would need actual logging implementation)
@router.get("/logs/activity", response_model=ActivityLogsResponse)
async def get_activity_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    action: Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get system activity logs"""
    # This would return actual activity logs
    # For now, return empty response
    return ActivityLogsResponse(
        logs=[],
        total_count=0,
        page=page,
        page_size=page_size,
        has_next=False
    ) 