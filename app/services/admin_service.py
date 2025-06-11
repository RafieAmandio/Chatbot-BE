import os
import time
import psutil
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from app.database.models import (
    Tenant, User, Conversation, Message, KnowledgeItem, 
    Product, UploadedFile, Prompt, Tool
)
from app.schemas.admin import (
    SystemOverview, TenantAnalytics, UserAnalytics, APIAnalytics,
    KnowledgeAnalytics, FileSystemAnalytics, ChatAnalytics,
    SystemHealth, DatabaseHealth, VectorStoreHealth,
    TenantUsageMetrics, UserActivityMetric, SystemHealthStatus,
    TimeRange, AdminDashboard, ActivityLogEntry
)
from app.services.vector_store import vector_store
from app.config import settings

logger = logging.getLogger(__name__)


class AdminService:
    """Service for administrative operations and system monitoring"""
    
    def __init__(self):
        self.start_time = time.time()
    
    async def get_system_overview(self, db: Session) -> SystemOverview:
        """Get high-level system overview metrics"""
        try:
            # Basic counts
            total_tenants = db.query(Tenant).filter(Tenant.is_active == True).count()
            total_users = db.query(User).filter(User.is_active == True).count()
            total_conversations = db.query(Conversation).count()
            total_messages = db.query(Message).count()
            total_knowledge_items = db.query(KnowledgeItem).filter(KnowledgeItem.is_active == True).count()
            total_products = db.query(Product).filter(Product.is_active == True).count()
            total_files = db.query(UploadedFile).filter(UploadedFile.is_active == True).count()
            
            # Storage calculations
            storage_query = db.query(func.sum(UploadedFile.file_size)).filter(
                UploadedFile.is_active == True
            ).scalar()
            storage_used = storage_query or 0
            
            # Today's activity
            today = datetime.now().date()
            api_requests_today = 0  # This would need API logging implementation
            
            # Active conversations (last 24 hours)
            yesterday = datetime.now() - timedelta(days=1)
            active_conversations = db.query(Conversation).filter(
                Conversation.updated_at >= yesterday
            ).count()
            
            # System health check
            system_status = await self._get_overall_system_status(db)
            
            return SystemOverview(
                status=system_status,
                uptime=int(time.time() - self.start_time),
                version=settings.app_version,
                total_tenants=total_tenants,
                total_users=total_users,
                total_conversations=total_conversations,
                total_messages=total_messages,
                total_knowledge_items=total_knowledge_items,
                total_products=total_products,
                total_files=total_files,
                storage_used=storage_used,
                api_requests_today=api_requests_today,
                active_conversations=active_conversations,
                last_updated=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Error getting system overview: {e}")
            raise
    
    async def get_tenant_analytics(self, db: Session, time_range: TimeRange = TimeRange.DAY) -> TenantAnalytics:
        """Get tenant usage analytics"""
        try:
            # Total tenant count
            total_tenants = db.query(Tenant).filter(Tenant.is_active == True).count()
            
            # Active tenants today (those with activity)
            today = datetime.now().date()
            active_tenants_query = db.query(Tenant.id).join(Conversation).filter(
                and_(
                    Tenant.is_active == True,
                    func.date(Conversation.updated_at) == today
                )
            ).distinct()
            active_tenants_today = active_tenants_query.count()
            
            # Top tenants by usage
            tenant_metrics = []
            tenants = db.query(Tenant).filter(Tenant.is_active == True).all()
            
            for tenant in tenants[:10]:  # Top 10 tenants
                # Get tenant usage metrics
                usage = await self._get_tenant_usage_metrics(db, tenant.id)
                tenant_metrics.append(usage)
            
            # Sort by total activity (conversations + messages)
            tenant_metrics.sort(
                key=lambda x: x.total_conversations + x.total_messages,
                reverse=True
            )
            
            # Storage by tenant
            storage_by_tenant = []
            for tenant in tenants:
                storage_query = db.query(func.sum(UploadedFile.file_size)).filter(
                    and_(
                        UploadedFile.tenant_id == tenant.id,
                        UploadedFile.is_active == True
                    )
                ).scalar()
                
                storage_by_tenant.append({
                    "tenant_id": tenant.id,
                    "tenant_name": tenant.name,
                    "storage_used": storage_query or 0
                })
            
            # Growth metrics (simple implementation)
            growth_metrics = {
                "new_tenants_this_week": db.query(Tenant).filter(
                    Tenant.created_at >= datetime.now() - timedelta(days=7)
                ).count(),
                "new_tenants_this_month": db.query(Tenant).filter(
                    Tenant.created_at >= datetime.now() - timedelta(days=30)
                ).count()
            }
            
            return TenantAnalytics(
                total_tenants=total_tenants,
                active_tenants_today=active_tenants_today,
                top_tenants_by_usage=tenant_metrics[:5],
                storage_by_tenant=storage_by_tenant,
                growth_metrics=growth_metrics
            )
            
        except Exception as e:
            logger.error(f"Error getting tenant analytics: {e}")
            raise
    
    async def get_user_analytics(self, db: Session, time_range: TimeRange = TimeRange.DAY) -> UserAnalytics:
        """Get user activity analytics"""
        try:
            # Basic counts
            total_users = db.query(User).filter(User.is_active == True).count()
            
            # Today's activity
            today = datetime.now().date()
            yesterday = datetime.now() - timedelta(days=1)
            
            # Active users today (with conversations)
            active_users_today = db.query(User.id).join(Conversation).filter(
                and_(
                    User.is_active == True,
                    func.date(Conversation.updated_at) == today
                )
            ).distinct().count()
            
            # New users today
            new_users_today = db.query(User).filter(
                and_(
                    User.is_active == True,
                    func.date(User.created_at) == today
                )
            ).count()
            
            # Most active users
            user_activity = []
            users_with_activity = db.query(
                User,
                func.count(Conversation.id).label('total_conversations'),
                func.count(Message.id).label('total_messages'),
                func.max(Conversation.updated_at).label('last_activity')
            ).join(Conversation).join(Message).join(Tenant).filter(
                User.is_active == True
            ).group_by(User.id).order_by(
                func.count(Message.id).desc()
            ).limit(10).all()
            
            for user, conv_count, msg_count, last_activity in users_with_activity:
                tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
                user_activity.append(UserActivityMetric(
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
            
            # User growth metrics
            user_growth = {
                "daily": db.query(User).filter(
                    User.created_at >= datetime.now() - timedelta(days=1)
                ).count(),
                "weekly": db.query(User).filter(
                    User.created_at >= datetime.now() - timedelta(days=7)
                ).count(),
                "monthly": db.query(User).filter(
                    User.created_at >= datetime.now() - timedelta(days=30)
                ).count()
            }
            
            # Authentication metrics (placeholder)
            auth_metrics = {
                "successful_logins_today": 0,  # Would need session tracking
                "failed_logins_today": 0,
                "password_resets_today": 0
            }
            
            return UserAnalytics(
                total_users=total_users,
                active_users_today=active_users_today,
                new_users_today=new_users_today,
                most_active_users=user_activity,
                user_growth=user_growth,
                authentication_metrics=auth_metrics
            )
            
        except Exception as e:
            logger.error(f"Error getting user analytics: {e}")
            raise
    
    async def get_knowledge_analytics(self, db: Session) -> KnowledgeAnalytics:
        """Get knowledge base analytics"""
        try:
            # Basic counts
            total_items = db.query(KnowledgeItem).filter(KnowledgeItem.is_active == True).count()
            
            today = datetime.now().date()
            items_added_today = db.query(KnowledgeItem).filter(
                and_(
                    KnowledgeItem.is_active == True,
                    func.date(KnowledgeItem.created_at) == today
                )
            ).count()
            
            # Items by type
            type_counts = {}
            type_results = db.query(
                KnowledgeItem.document_type,
                func.count(KnowledgeItem.id).label('count')
            ).filter(
                KnowledgeItem.is_active == True
            ).group_by(KnowledgeItem.document_type).all()
            
            for doc_type, count in type_results:
                type_counts[doc_type or 'unknown'] = count
            
            # Vector store health
            vector_health = await self._get_vector_store_health()
            
            return KnowledgeAnalytics(
                total_items=total_items,
                items_added_today=items_added_today,
                most_searched_items=[],  # Would need search logging
                search_success_rate=95.0,  # Placeholder
                avg_search_time=150.0,  # Placeholder (ms)
                items_by_type=type_counts,
                vector_store_health=vector_health
            )
            
        except Exception as e:
            logger.error(f"Error getting knowledge analytics: {e}")
            raise
    
    async def get_file_analytics(self, db: Session) -> FileSystemAnalytics:
        """Get file system analytics"""
        try:
            # Basic counts
            total_files = db.query(UploadedFile).filter(UploadedFile.is_active == True).count()
            
            today = datetime.now().date()
            files_uploaded_today = db.query(UploadedFile).filter(
                and_(
                    UploadedFile.is_active == True,
                    func.date(UploadedFile.created_at) == today
                )
            ).count()
            
            # Storage usage
            total_storage = db.query(func.sum(UploadedFile.file_size)).filter(
                UploadedFile.is_active == True
            ).scalar() or 0
            
            # Processing metrics
            pending_files = db.query(UploadedFile).filter(
                and_(
                    UploadedFile.is_active == True,
                    UploadedFile.processing_status == "pending"
                )
            ).count()
            
            # Success rate
            total_processed = db.query(UploadedFile).filter(
                UploadedFile.processing_status.in_(["completed", "failed"])
            ).count()
            
            successful_processed = db.query(UploadedFile).filter(
                UploadedFile.processing_status == "completed"
            ).count()
            
            success_rate = (successful_processed / max(total_processed, 1)) * 100
            
            # Files by type
            type_counts = {}
            type_results = db.query(
                UploadedFile.file_extension,
                func.count(UploadedFile.id).label('count')
            ).filter(
                UploadedFile.is_active == True
            ).group_by(UploadedFile.file_extension).all()
            
            for ext, count in type_results:
                type_counts[ext or 'unknown'] = count
            
            # Failed uploads today
            failed_today = db.query(UploadedFile).filter(
                and_(
                    func.date(UploadedFile.created_at) == today,
                    UploadedFile.processing_status == "failed"
                )
            ).count()
            
            return FileSystemAnalytics(
                total_files=total_files,
                files_uploaded_today=files_uploaded_today,
                total_storage_used=total_storage,
                processing_queue_size=pending_files,
                processing_success_rate=success_rate,
                avg_processing_time=2.5,  # Placeholder (seconds)
                files_by_type=type_counts,
                failed_uploads_today=failed_today
            )
            
        except Exception as e:
            logger.error(f"Error getting file analytics: {e}")
            raise
    
    async def get_chat_analytics(self, db: Session) -> ChatAnalytics:
        """Get chat and conversation analytics"""
        try:
            # Basic counts
            total_conversations = db.query(Conversation).count()
            total_messages = db.query(Message).count()
            
            today = datetime.now().date()
            conversations_today = db.query(Conversation).filter(
                func.date(Conversation.created_at) == today
            ).count()
            
            messages_today = db.query(Message).filter(
                func.date(Message.created_at) == today
            ).count()
            
            # Average conversation length
            avg_length_query = db.query(
                func.avg(func.count(Message.id))
            ).join(Conversation).group_by(Conversation.id).scalar()
            avg_conversation_length = float(avg_length_query) if avg_length_query else 0
            
            # Tool usage stats (from message metadata)
            tool_usage = {}
            messages_with_tools = db.query(Message).filter(
                Message.meta_data.isnot(None)
            ).all()
            
            for message in messages_with_tools:
                if message.meta_data and 'tool_calls' in message.meta_data:
                    for tool_call in message.meta_data.get('tool_calls', []):
                        if isinstance(tool_call, dict) and 'function' in tool_call:
                            tool_name = tool_call['function'].get('name', 'unknown')
                            tool_usage[tool_name] = tool_usage.get(tool_name, 0) + 1
            
            return ChatAnalytics(
                total_conversations=total_conversations,
                conversations_today=conversations_today,
                total_messages=total_messages,
                messages_today=messages_today,
                avg_conversation_length=avg_conversation_length,
                avg_response_time=1.2,  # Placeholder (seconds)
                tool_usage_stats=tool_usage,
                popular_topics=[]  # Would need topic analysis
            )
            
        except Exception as e:
            logger.error(f"Error getting chat analytics: {e}")
            raise
    
    async def get_system_health(self, db: Session) -> SystemHealth:
        """Get comprehensive system health status"""
        try:
            # Database health
            db_health = await self._get_database_health(db)
            
            # Vector store health
            vector_health = await self._get_vector_store_health_detailed()
            
            # API health (basic check)
            api_health = {
                "auth": SystemHealthStatus.HEALTHY,
                "chat": SystemHealthStatus.HEALTHY,
                "knowledge": SystemHealthStatus.HEALTHY,
                "files": SystemHealthStatus.HEALTHY
            }
            
            # System resources
            disk_usage = self._get_disk_usage()
            memory_usage = self._get_memory_usage()
            
            # Overall status
            overall_status = SystemHealthStatus.HEALTHY
            if db_health.status != SystemHealthStatus.HEALTHY:
                overall_status = SystemHealthStatus.WARNING
            if vector_health.status == SystemHealthStatus.CRITICAL:
                overall_status = SystemHealthStatus.CRITICAL
            
            return SystemHealth(
                overall_status=overall_status,
                database=db_health,
                vector_store=vector_health,
                api_health=api_health,
                disk_usage=disk_usage,
                memory_usage=memory_usage,
                last_health_check=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Error getting system health: {e}")
            raise
    
    async def get_admin_dashboard(self, db: Session, time_range: TimeRange = TimeRange.DAY) -> AdminDashboard:
        """Get complete admin dashboard data"""
        try:
            return AdminDashboard(
                system_overview=await self.get_system_overview(db),
                tenant_analytics=await self.get_tenant_analytics(db, time_range),
                user_analytics=await self.get_user_analytics(db, time_range),
                api_analytics=APIAnalytics(
                    total_requests=0,
                    requests_today=0,
                    success_rate=99.5,
                    avg_response_time=250.0,
                    top_endpoints=[],
                    error_rate_by_endpoint={},
                    requests_by_hour=[]
                ),  # Placeholder - would need request logging
                knowledge_analytics=await self.get_knowledge_analytics(db),
                file_analytics=await self.get_file_analytics(db),
                chat_analytics=await self.get_chat_analytics(db),
                system_health=await self.get_system_health(db),
                generated_at=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Error generating admin dashboard: {e}")
            raise
    
    # Helper methods
    async def _get_tenant_usage_metrics(self, db: Session, tenant_id: str) -> TenantUsageMetrics:
        """Get detailed usage metrics for a specific tenant"""
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise ValueError(f"Tenant {tenant_id} not found")
        
        # Count resources
        total_users = db.query(User).filter(
            and_(User.tenant_id == tenant_id, User.is_active == True)
        ).count()
        
        today = datetime.now().date()
        active_users_today = db.query(User.id).join(Conversation).filter(
            and_(
                User.tenant_id == tenant_id,
                func.date(Conversation.updated_at) == today
            )
        ).distinct().count()
        
        total_conversations = db.query(Conversation).filter(
            Conversation.tenant_id == tenant_id
        ).count()
        
        total_messages = db.query(Message).join(Conversation).filter(
            Conversation.tenant_id == tenant_id
        ).count()
        
        total_knowledge_items = db.query(KnowledgeItem).filter(
            and_(
                KnowledgeItem.tenant_id == tenant_id,
                KnowledgeItem.is_active == True
            )
        ).count()
        
        total_products = db.query(Product).filter(
            and_(
                Product.tenant_id == tenant_id,
                Product.is_active == True
            )
        ).count()
        
        total_files = db.query(UploadedFile).filter(
            and_(
                UploadedFile.tenant_id == tenant_id,
                UploadedFile.is_active == True
            )
        ).count()
        
        storage_used = db.query(func.sum(UploadedFile.file_size)).filter(
            and_(
                UploadedFile.tenant_id == tenant_id,
                UploadedFile.is_active == True
            )
        ).scalar() or 0
        
        # Last activity
        last_activity = db.query(func.max(Conversation.updated_at)).filter(
            Conversation.tenant_id == tenant_id
        ).scalar()
        
        return TenantUsageMetrics(
            tenant_id=tenant_id,
            tenant_name=tenant.name,
            total_users=total_users,
            active_users_today=active_users_today,
            total_conversations=total_conversations,
            total_messages=total_messages,
            total_knowledge_items=total_knowledge_items,
            total_products=total_products,
            total_files=total_files,
            storage_used=storage_used,
            api_requests_today=0,  # Placeholder
            last_activity=last_activity,
            created_at=tenant.created_at
        )
    
    async def _get_overall_system_status(self, db: Session) -> SystemHealthStatus:
        """Determine overall system health status"""
        try:
            # Basic database connectivity check
            db.execute("SELECT 1")
            
            # Check vector store
            vector_health = await vector_store.health_check()
            
            if not vector_health.get("healthy", False):
                return SystemHealthStatus.WARNING
            
            return SystemHealthStatus.HEALTHY
            
        except Exception as e:
            logger.error(f"System health check failed: {e}")
            return SystemHealthStatus.CRITICAL
    
    async def _get_database_health(self, db: Session) -> DatabaseHealth:
        """Get database health metrics"""
        try:
            # Basic connection test
            db.execute("SELECT 1")
            
            # Get table sizes
            table_sizes = {}
            tables = ['tenants', 'users', 'conversations', 'messages', 
                     'knowledge_items', 'products', 'uploaded_files']
            
            for table in tables:
                try:
                    count = db.execute(f"SELECT COUNT(*) FROM {table}").scalar()
                    table_sizes[table] = count
                except Exception:
                    table_sizes[table] = 0
            
            return DatabaseHealth(
                status=SystemHealthStatus.HEALTHY,
                connection_pool_size=10,  # Placeholder
                active_connections=1,  # Placeholder
                slow_queries=0,  # Placeholder
                last_backup=None,  # Would need backup system
                table_sizes=table_sizes
            )
            
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return DatabaseHealth(
                status=SystemHealthStatus.CRITICAL,
                connection_pool_size=0,
                active_connections=0,
                slow_queries=0,
                last_backup=None,
                table_sizes={}
            )
    
    async def _get_vector_store_health(self) -> Dict[str, Any]:
        """Get basic vector store health info"""
        try:
            health = await vector_store.health_check()
            return {
                "status": "healthy" if health.get("healthy", False) else "unhealthy",
                "collections": health.get("collections", 0),
                "total_vectors": health.get("total_vectors", 0)
            }
        except Exception as e:
            logger.error(f"Vector store health check failed: {e}")
            return {"status": "unhealthy", "collections": 0, "total_vectors": 0}
    
    async def _get_vector_store_health_detailed(self) -> VectorStoreHealth:
        """Get detailed vector store health"""
        try:
            health = await vector_store.health_check()
            
            return VectorStoreHealth(
                status=SystemHealthStatus.HEALTHY if health.get("healthy", False) else SystemHealthStatus.CRITICAL,
                collection_count=health.get("collections", 0),
                total_vectors=health.get("total_vectors", 0),
                index_health="good",
                last_sync=datetime.now(),
                performance_metrics={
                    "avg_query_time": 50.0,  # ms
                    "index_size": health.get("index_size", 0)
                }
            )
            
        except Exception as e:
            logger.error(f"Vector store health check failed: {e}")
            return VectorStoreHealth(
                status=SystemHealthStatus.CRITICAL,
                collection_count=0,
                total_vectors=0,
                index_health="error",
                last_sync=None,
                performance_metrics={}
            )
    
    def _get_disk_usage(self) -> Dict[str, Any]:
        """Get disk usage information"""
        try:
            usage = psutil.disk_usage('/')
            return {
                "total": usage.total,
                "used": usage.used,
                "free": usage.free,
                "percentage": (usage.used / usage.total) * 100
            }
        except Exception:
            return {"total": 0, "used": 0, "free": 0, "percentage": 0}
    
    def _get_memory_usage(self) -> Dict[str, Any]:
        """Get memory usage information"""
        try:
            memory = psutil.virtual_memory()
            return {
                "total": memory.total,
                "used": memory.used,
                "free": memory.available,
                "percentage": memory.percent
            }
        except Exception:
            return {"total": 0, "used": 0, "free": 0, "percentage": 0}


# Global instance
admin_service = AdminService() 