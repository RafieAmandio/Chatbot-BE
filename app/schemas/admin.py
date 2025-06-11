from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from enum import Enum


class SystemHealthStatus(str, Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    MAINTENANCE = "maintenance"


class TimeRange(str, Enum):
    HOUR = "1h"
    DAY = "24h"
    WEEK = "7d"
    MONTH = "30d"
    QUARTER = "90d"
    YEAR = "365d"


class MetricType(str, Enum):
    COUNT = "count"
    PERCENTAGE = "percentage"
    BYTES = "bytes"
    MILLISECONDS = "milliseconds"
    RATE = "rate"


# System Overview Schemas
class SystemMetric(BaseModel):
    name: str
    value: Union[int, float, str]
    unit: MetricType
    trend: Optional[float] = None  # Percentage change
    status: Optional[SystemHealthStatus] = None


class SystemOverview(BaseModel):
    status: SystemHealthStatus
    uptime: int  # seconds
    version: str
    total_tenants: int
    total_users: int
    total_conversations: int
    total_messages: int
    total_knowledge_items: int
    total_products: int
    total_files: int
    storage_used: int  # bytes
    api_requests_today: int
    active_conversations: int
    last_updated: datetime


# Tenant Analytics
class TenantUsageMetrics(BaseModel):
    tenant_id: str
    tenant_name: str
    total_users: int
    active_users_today: int
    total_conversations: int
    total_messages: int
    total_knowledge_items: int
    total_products: int
    total_files: int
    storage_used: int
    api_requests_today: int
    last_activity: Optional[datetime]
    created_at: datetime


class TenantAnalytics(BaseModel):
    total_tenants: int
    active_tenants_today: int
    top_tenants_by_usage: List[TenantUsageMetrics]
    storage_by_tenant: List[Dict[str, Any]]
    growth_metrics: Dict[str, Any]


# User Analytics
class UserActivityMetric(BaseModel):
    user_id: str
    email: str
    full_name: Optional[str]
    tenant_name: str
    total_conversations: int
    total_messages: int
    last_activity: Optional[datetime]
    signup_date: datetime
    is_active: bool


class UserAnalytics(BaseModel):
    total_users: int
    active_users_today: int
    new_users_today: int
    most_active_users: List[UserActivityMetric]
    user_growth: Dict[str, int]  # Daily/weekly/monthly growth
    authentication_metrics: Dict[str, int]


# API Analytics
class APIEndpointMetric(BaseModel):
    endpoint: str
    method: str
    total_requests: int
    success_rate: float
    avg_response_time: float
    error_count: int
    last_called: Optional[datetime]


class APIAnalytics(BaseModel):
    total_requests: int
    requests_today: int
    success_rate: float
    avg_response_time: float
    top_endpoints: List[APIEndpointMetric]
    error_rate_by_endpoint: Dict[str, float]
    requests_by_hour: List[Dict[str, Any]]


# Knowledge Base Analytics
class KnowledgeAnalytics(BaseModel):
    total_items: int
    items_added_today: int
    most_searched_items: List[Dict[str, Any]]
    search_success_rate: float
    avg_search_time: float
    items_by_type: Dict[str, int]
    vector_store_health: Dict[str, Any]


# File System Analytics
class FileSystemAnalytics(BaseModel):
    total_files: int
    files_uploaded_today: int
    total_storage_used: int
    processing_queue_size: int
    processing_success_rate: float
    avg_processing_time: float
    files_by_type: Dict[str, int]
    failed_uploads_today: int


# Chat Analytics
class ChatAnalytics(BaseModel):
    total_conversations: int
    conversations_today: int
    total_messages: int
    messages_today: int
    avg_conversation_length: float
    avg_response_time: float
    tool_usage_stats: Dict[str, int]
    popular_topics: List[Dict[str, Any]]


# System Health
class DatabaseHealth(BaseModel):
    status: SystemHealthStatus
    connection_pool_size: int
    active_connections: int
    slow_queries: int
    last_backup: Optional[datetime]
    table_sizes: Dict[str, int]


class VectorStoreHealth(BaseModel):
    status: SystemHealthStatus
    collection_count: int
    total_vectors: int
    index_health: str
    last_sync: Optional[datetime]
    performance_metrics: Dict[str, float]


class SystemHealth(BaseModel):
    overall_status: SystemHealthStatus
    database: DatabaseHealth
    vector_store: VectorStoreHealth
    api_health: Dict[str, SystemHealthStatus]
    disk_usage: Dict[str, Any]
    memory_usage: Dict[str, Any]
    last_health_check: datetime


# Configuration Management
class TenantConfiguration(BaseModel):
    tenant_id: str
    max_users: int
    max_documents: int
    max_products: int
    storage_limit: int
    api_rate_limit: int
    features_enabled: List[str]
    custom_settings: Dict[str, Any]


class SystemConfiguration(BaseModel):
    maintenance_mode: bool
    registration_enabled: bool
    file_upload_enabled: bool
    max_file_size: int
    supported_file_types: List[str]
    default_tenant_limits: TenantConfiguration
    backup_schedule: str
    log_retention_days: int


# Admin Actions
class TenantAction(BaseModel):
    action: str  # activate, deactivate, upgrade, downgrade
    tenant_id: str
    parameters: Optional[Dict[str, Any]] = None
    reason: Optional[str] = None


class UserAction(BaseModel):
    action: str  # activate, deactivate, reset_password, change_role
    user_id: str
    parameters: Optional[Dict[str, Any]] = None
    reason: Optional[str] = None


class SystemAction(BaseModel):
    action: str  # maintenance, backup, cleanup, restart
    parameters: Optional[Dict[str, Any]] = None
    scheduled_for: Optional[datetime] = None


# Activity Logs
class ActivityLogEntry(BaseModel):
    id: str
    timestamp: datetime
    user_id: Optional[str]
    tenant_id: Optional[str]
    action: str
    resource_type: str
    resource_id: Optional[str]
    details: Dict[str, Any]
    ip_address: Optional[str]
    user_agent: Optional[str]


class ActivityLogsResponse(BaseModel):
    logs: List[ActivityLogEntry]
    total_count: int
    page: int
    page_size: int
    has_next: bool


# Dashboard Requests
class AnalyticsRequest(BaseModel):
    time_range: TimeRange = TimeRange.DAY
    tenant_id: Optional[str] = None
    include_details: bool = False


class LogsRequest(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=100)
    action: Optional[str] = None
    resource_type: Optional[str] = None
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


# Response Models
class AdminDashboard(BaseModel):
    system_overview: SystemOverview
    tenant_analytics: TenantAnalytics
    user_analytics: UserAnalytics
    api_analytics: APIAnalytics
    knowledge_analytics: KnowledgeAnalytics
    file_analytics: FileSystemAnalytics
    chat_analytics: ChatAnalytics
    system_health: SystemHealth
    generated_at: datetime


class BatchActionResult(BaseModel):
    action: str
    total_items: int
    successful: int
    failed: int
    errors: List[str]
    execution_time: float 