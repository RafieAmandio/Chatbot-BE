from fastapi import HTTPException, status, Depends
from sqlalchemy.orm import Session
from typing import Optional

from app.database.connection import get_db
from app.database.models import User, Tenant
from app.auth.dependencies import get_current_user, get_current_tenant


class AdminMiddleware:
    """Middleware for handling admin authorization"""
    
    @staticmethod
    def require_admin_access():
        """Dependency that ensures the current user has admin access"""
        def check_admin(
            current_user: User = Depends(get_current_user),
            current_tenant: Tenant = Depends(get_current_tenant)
        ) -> User:
            if not current_user.is_admin:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Admin access required"
                )
            return current_user
        
        return check_admin
    
    @staticmethod
    def require_super_admin_access():
        """Dependency that ensures the current user is a super admin"""
        def check_super_admin(
            current_user: User = Depends(get_current_user),
            db: Session = Depends(get_db)
        ) -> User:
            # Super admin is admin on default tenant
            if not current_user.is_admin:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Super admin access required"
                )
            
            # Check if user is on default tenant (super admin)
            tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
            if not tenant or tenant.domain != "default":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Super admin access required"
                )
            
            return current_user
        
        return check_super_admin
    
    @staticmethod
    def require_tenant_admin_or_super_admin(tenant_id: Optional[str] = None):
        """Dependency that allows tenant admins to access their own data or super admins"""
        def check_access(
            current_user: User = Depends(get_current_user),
            current_tenant: Tenant = Depends(get_current_tenant),
            db: Session = Depends(get_db)
        ) -> User:
            if not current_user.is_admin:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Admin access required"
                )
            
            # Super admin can access anything
            if current_tenant.domain == "default":
                return current_user
            
            # Tenant admin can only access their own tenant data
            if tenant_id and tenant_id != current_tenant.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied for this tenant"
                )
            
            return current_user
        
        return check_access


# Create instances for easy importing
require_admin = AdminMiddleware.require_admin_access()
require_super_admin = AdminMiddleware.require_super_admin_access()
require_tenant_admin_or_super_admin = AdminMiddleware.require_tenant_admin_or_super_admin() 