# Multi-Tenant RAG Chatbot - API Documentation

## Overview

This is a comprehensive API documentation for the Multi-Tenant RAG (Retrieval-Augmented Generation) Chatbot Backend built with FastAPI. The system provides a multi-tenant architecture with OpenAI integration, vector-based knowledge retrieval, file processing, and administrative dashboard capabilities.

**Base URL**: `http://localhost:8000/api/v1`  
**Version**: 1.0.0  
**Total Endpoints**: 57

## Table of Contents

1. [Authentication](#authentication)
2. [Chat & Conversations](#chat--conversations)
3. [Tenant Management](#tenant-management)
4. [User Management](#user-management)
5. [Knowledge Management](#knowledge-management)
6. [Product Management](#product-management)
7. [Prompt Management](#prompt-management)
8. [File Upload System](#file-upload-system)
9. [Admin Dashboard](#admin-dashboard)
10. [System Health](#system-health)
11. [Error Responses](#error-responses)
12. [Rate Limiting](#rate-limiting)

---

## Authentication

All API endpoints (except registration and login) require JWT token authentication.

### Headers
```
Authorization: Bearer <jwt_token>
Content-Type: application/json
```

### Auth Endpoints

#### 1. Register User
```http
POST /auth/register
```

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securepassword123",
  "name": "John Doe",
  "company_name": "Example Corp",
  "is_admin": false
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "user": {
    "id": "uuid-string",
    "email": "user@example.com",
    "full_name": "John Doe",
    "is_admin": false,
    "tenant_id": "tenant-uuid"
  }
}
```

#### 2. Login
```http
POST /auth/login
```

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "user": {
    "id": "uuid-string",
    "email": "user@example.com",
    "full_name": "John Doe",
    "is_admin": false,
    "tenant_id": "tenant-uuid"
  }
}
```

#### 3. Get Current User
```http
GET /auth/me
```

**Response:**
```json
{
  "id": "uuid-string",
  "email": "user@example.com",
  "full_name": "John Doe",
  "is_admin": false,
  "tenant_id": "tenant-uuid",
  "created_at": "2024-01-01T00:00:00Z"
}
```

#### 4. Update Profile
```http
PUT /auth/me
```

**Request Body:**
```json
{
  "full_name": "John Updated Doe",
  "email": "newemail@example.com"
}
```

#### 5. Change Password
```http
POST /auth/change-password
```

**Request Body:**
```json
{
  "current_password": "oldpassword",
  "new_password": "newpassword123"
}
```

#### 6. Password Reset Request
```http
POST /auth/password-reset
```

**Request Body:**
```json
{
  "email": "user@example.com"
}
```

#### 7. Verify Token
```http
GET /auth/verify-token
```

---

## Chat & Conversations

### Chat Endpoints

#### 1. Send Chat Message (Non-Streaming)
```http
POST /chat/
```

**Request Body:**
```json
{
  "message": "What is your return policy?",
  "conversation_id": "conv-uuid-optional",
  "temperature": 0.7,
  "max_tokens": 1000
}
```

**Response:**
```json
{
  "conversation_id": "conv-uuid",
  "message": {
    "role": "assistant",
    "content": "Our return policy allows...",
    "metadata": {
      "tool_calls": []
    }
  },
  "usage": {
    "prompt_tokens": 150,
    "completion_tokens": 75,
    "total_tokens": 225
  }
}
```

#### 2. Stream Chat Response
```http
POST /chat/stream
```

**Request Body:** Same as non-streaming

**Response:** Server-Sent Events (SSE)
```
data: {"type": "conversation_id", "data": "conv-uuid"}

data: {"type": "content", "data": "Our return"}

data: {"type": "content", "data": " policy allows"}

data: {"type": "done", "data": "Stream completed"}
```

#### 3. Create Conversation
```http
POST /chat/conversations
```

**Request Body:**
```json
{
  "title": "Customer Support Chat"
}
```

**Response:**
```json
{
  "id": "conv-uuid",
  "title": "Customer Support Chat",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z",
  "messages": []
}
```

#### 4. List Conversations
```http
GET /chat/conversations
```

**Response:**
```json
[
  {
    "id": "conv-uuid",
    "title": "Customer Support Chat",
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z",
    "messages": []
  }
]
```

#### 5. Get Conversation with Messages
```http
GET /chat/conversations/{conversation_id}
```

**Response:**
```json
{
  "id": "conv-uuid",
  "title": "Customer Support Chat",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z",
  "messages": [
    {
      "role": "user",
      "content": "Hello",
      "metadata": null
    },
    {
      "role": "assistant", 
      "content": "Hi! How can I help you?",
      "metadata": null
    }
  ]
}
```

---

## Tenant Management

#### 1. Create Tenant
```http
POST /tenants/
```

**Request Body:**
```json
{
  "name": "New Company",
  "domain": "newcompany.com",
  "description": "A new tenant company",
  "max_users": 100,
  "max_documents": 1000,
  "max_products": 500
}
```

#### 2. List Tenants
```http
GET /tenants/
```

**Query Parameters:**
- `skip`: int (default: 0)
- `limit`: int (default: 100)

#### 3. Get Tenant Details
```http
GET /tenants/{tenant_id}
```

---

## User Management

#### 1. Create User
```http
POST /auth/users
```

**Request Body:**
```json
{
  "email": "newuser@example.com",
  "password": "password123",
  "full_name": "New User",
  "is_admin": false
}
```

#### 2. List Users
```http
GET /users/
```

**Query Parameters:**
- `skip`: int (default: 0)
- `limit`: int (default: 100)

#### 3. Get User Details
```http
GET /users/{user_id}
```

---

## Knowledge Management

### Knowledge Base Endpoints

#### 1. Create Knowledge Item
```http
POST /knowledge/
```

**Request Body:**
```json
{
  "title": "Shipping Policy",
  "content": "We offer free shipping on orders over $50...",
  "source": "policy_docs",
  "document_type": "policy",
  "meta_data": {
    "category": "shipping",
    "tags": ["policy", "shipping"]
  }
}
```

**Response:**
```json
{
  "id": "knowledge-uuid",
  "tenant_id": "tenant-uuid", 
  "title": "Shipping Policy",
  "content": "We offer free shipping...",
  "source": "policy_docs",
  "document_type": "policy",
  "meta_data": {
    "category": "shipping",
    "tags": ["policy", "shipping"]
  },
  "is_active": true,
  "created_at": "2024-01-01T00:00:00Z",
  "vector_id": "vector-id"
}
```

#### 2. List Knowledge Items
```http
GET /knowledge/
```

**Query Parameters:**
- `skip`: int (default: 0)
- `limit`: int (default: 100) 
- `search`: string (optional)
- `document_type`: string (optional)

#### 3. Search Knowledge Base
```http
POST /knowledge/search
```

**Request Body:**
```json
{
  "query": "return policy",
  "limit": 10,
  "min_score": 0.7
}
```

**Response:**
```json
[
  {
    "item": {
      "id": "knowledge-uuid",
      "title": "Return Policy",
      "content": "Items can be returned...",
      "source": "policy_docs",
      "document_type": "policy"
    },
    "score": 0.95
  }
]
```

#### 4. Get Knowledge Item
```http
GET /knowledge/{item_id}
```

#### 5. Update Knowledge Item
```http
PUT /knowledge/{item_id}
```

#### 6. Delete Knowledge Item
```http
DELETE /knowledge/{item_id}
```

#### 7. List Document Types
```http
GET /knowledge/types/list
```

---

## Product Management

### Product Endpoints

#### 1. Create Product
```http
POST /products/
```

**Request Body:**
```json
{
  "name": "Premium Headphones",
  "description": "High-quality noise-canceling headphones",
  "category": "Electronics",
  "price": 299.99,
  "sku": "HPH-001",
  "stock_quantity": 50,
  "specifications": {
    "brand": "AudioTech",
    "color": "Black",
    "warranty": "2 years"
  }
}
```

**Response:**
```json
{
  "id": "product-uuid",
  "tenant_id": "tenant-uuid",
  "name": "Premium Headphones",
  "description": "High-quality noise-canceling headphones",
  "category": "Electronics", 
  "price": 299.99,
  "sku": "HPH-001",
  "stock_quantity": 50,
  "specifications": {
    "brand": "AudioTech",
    "color": "Black", 
    "warranty": "2 years"
  },
  "is_active": true,
  "created_at": "2024-01-01T00:00:00Z",
  "vector_id": "vector-id"
}
```

#### 2. List Products
```http
GET /products/
```

**Query Parameters:**
- `skip`: int (default: 0)
- `limit`: int (default: 100)
- `category`: string (optional)
- `search`: string (optional)

#### 3. Search Products
```http
POST /products/search
```

**Request Body:**
```json
{
  "query": "wireless headphones",
  "category": "Electronics",
  "min_price": 100,
  "max_price": 500,
  "limit": 20
}
```

#### 4. Get Product Details
```http
GET /products/{product_id}
```

#### 5. Update Product
```http
PUT /products/{product_id}
```

#### 6. Delete Product
```http
DELETE /products/{product_id}
```

#### 7. Update Stock Quantity
```http
PUT /products/{product_id}/stock
```

**Request Body:**
```json
{
  "stock_quantity": 25
}
```

#### 8. List Product Categories
```http
GET /products/categories/list
```

---

## Prompt Management

### Prompt System Endpoints

#### 1. Create Prompt
```http
POST /prompts/
```

**Request Body:**
```json
{
  "name": "Customer Service Assistant",
  "system_prompt": "You are a helpful customer service assistant...",
  "description": "Main prompt for customer interactions",
  "variables": {
    "company_name": "string",
    "support_hours": "string"
  }
}
```

**Response:**
```json
{
  "id": "prompt-uuid",
  "tenant_id": "tenant-uuid",
  "name": "Customer Service Assistant",
  "system_prompt": "You are a helpful customer service assistant...",
  "description": "Main prompt for customer interactions",
  "variables": {
    "company_name": "string",
    "support_hours": "string"
  },
  "is_active": true,
  "is_default": false,
  "created_at": "2024-01-01T00:00:00Z"
}
```

#### 2. List Prompts
```http
GET /prompts/
```

#### 3. Get Current Default Prompt
```http
GET /prompts/default/current
```

#### 4. Set Default Prompt
```http
POST /prompts/{prompt_id}/set-default
```

#### 5. Test Prompt
```http
POST /prompts/test
```

**Request Body:**
```json
{
  "prompt_id": "prompt-uuid",
  "test_message": "Hello, can you help me?",
  "variables": {
    "company_name": "Example Corp",
    "support_hours": "9 AM - 5 PM"
  }
}
```

#### 6. Get Prompt Variables
```http
GET /prompts/{prompt_id}/variables
```

#### 7. Update/Delete Prompts
```http
PUT /prompts/{prompt_id}
DELETE /prompts/{prompt_id}
```

---

## File Upload System

### File Management Endpoints

#### 1. Upload Single File
```http
POST /files/upload
```

**Request:** Multipart Form Data
```
file: <file_binary>
auto_create_knowledge: true
document_type: "pdf"
custom_metadata: {"source": "user_upload"}
```

**Response:**
```json
{
  "file_id": "file-uuid",
  "filename": "document.pdf",
  "success": true,
  "text_extracted": true,
  "text_length": 5420,
  "word_count": 867,
  "knowledge_items_created": 3,
  "processing_time": 2.45,
  "metadata": {
    "file_size": 1024000,
    "pages": 10,
    "format": "PDF"
  }
}
```

#### 2. Bulk File Upload
```http
POST /files/upload/bulk
```

**Request:** Multipart Form Data (up to 20 files)

**Response:**
```json
{
  "total_files": 5,
  "successful_uploads": 4,
  "failed_uploads": 1,
  "results": [
    {
      "file_id": "file-uuid-1",
      "filename": "doc1.pdf",
      "success": true,
      "knowledge_items_created": 2
    }
  ],
  "total_processing_time": 8.7
}
```

#### 3. List Uploaded Files
```http
GET /files/
```

**Query Parameters:**
- `skip`: int (default: 0)
- `limit`: int (default: 100)
- `file_type`: string (optional)
- `processing_status`: string (optional)

**Response:**
```json
[
  {
    "id": "file-uuid",
    "tenant_id": "tenant-uuid",
    "original_filename": "document.pdf",
    "file_extension": "pdf",
    "file_size": 1024000,
    "processing_status": "completed",
    "knowledge_items_created": 3,
    "created_at": "2024-01-01T00:00:00Z",
    "processed_at": "2024-01-01T00:01:30Z"
  }
]
```

#### 4. Get File Details
```http
GET /files/{file_id}
```

#### 5. Delete File
```http
DELETE /files/{file_id}
```

#### 6. File Statistics
```http
GET /files/stats/overview
```

**Response:**
```json
{
  "total_files": 150,
  "total_storage_used": 52428800,
  "files_by_type": {
    "pdf": 45,
    "docx": 30,
    "txt": 25
  },
  "processing_stats": {
    "completed": 140,
    "failed": 5,
    "pending": 5
  },
  "avg_processing_time": 2.3
}
```

#### 7. Manual Document Splitting
```http
POST /files/document/split
```

**Request Body:**
```json
{
  "content": "Long document content...",
  "title": "Document Title",
  "max_chunk_size": 5000,
  "chunk_overlap": 200,
  "source": "manual_input",
  "document_type": "text"
}
```

#### 8. Supported File Formats
```http
GET /files/supported-formats
```

**Response:**
```json
{
  "supported_formats": [
    {
      "extension": "pdf",
      "mime_types": ["application/pdf"],
      "description": "Portable Document Format"
    },
    {
      "extension": "docx", 
      "mime_types": ["application/vnd.openxmlformats-officedocument.wordprocessingml.document"],
      "description": "Microsoft Word Document"
    }
  ]
}
```

---

## Admin Dashboard

**Note:** All admin endpoints require admin privileges.

### System Overview

#### 1. Admin Dashboard
```http
GET /admin/dashboard
```

**Query Parameters:**
- `time_range`: string (1h, 24h, 7d, 30d)
- `tenant_id`: string (super admin only)
- `include_details`: boolean

**Response:**
```json
{
  "system_overview": {
    "status": "healthy",
    "uptime": 86400,
    "version": "1.0.0",
    "total_tenants": 15,
    "total_users": 150,
    "total_conversations": 1250,
    "total_messages": 8500,
    "total_knowledge_items": 450,
    "total_products": 300,
    "total_files": 200,
    "storage_used": 1073741824,
    "api_requests_today": 2500,
    "active_conversations": 25
  },
  "tenant_analytics": {...},
  "user_analytics": {...},
  "knowledge_analytics": {...},
  "file_analytics": {...},
  "chat_analytics": {...},
  "system_health": {...}
}
```

#### 2. System Overview
```http
GET /admin/overview
```

#### 3. System Health Check
```http
GET /admin/health
```

**Response:**
```json
{
  "overall_status": "healthy",
  "database": {
    "status": "healthy",
    "connection_pool_size": 10,
    "active_connections": 3,
    "slow_queries": 0,
    "table_sizes": {
      "users": 150,
      "conversations": 1250,
      "knowledge_items": 450
    }
  },
  "vector_store": {
    "status": "healthy",
    "collection_count": 8,
    "total_vectors": 2500,
    "index_health": "good",
    "performance_metrics": {
      "avg_query_time": 45.2
    }
  },
  "disk_usage": {
    "total": 107374182400,
    "used": 21474836480,
    "free": 85899345920,
    "percentage": 20.0
  },
  "memory_usage": {
    "total": 8589934592,
    "used": 4294967296,
    "free": 4294967296,
    "percentage": 50.0
  }
}
```

### Analytics Endpoints

#### 4. Tenant Analytics
```http
GET /admin/analytics/tenants
```

**Response:**
```json
{
  "total_tenants": 15,
  "active_tenants_today": 8,
  "top_tenants_by_usage": [
    {
      "tenant_id": "tenant-uuid",
      "tenant_name": "Company A",
      "total_users": 25,
      "active_users_today": 12,
      "total_conversations": 200,
      "total_messages": 1500,
      "storage_used": 104857600
    }
  ],
  "growth_metrics": {
    "new_tenants_this_week": 2,
    "new_tenants_this_month": 5
  }
}
```

#### 5. User Analytics
```http
GET /admin/analytics/users
```

#### 6. Knowledge Analytics
```http
GET /admin/analytics/knowledge
```

#### 7. File Analytics
```http
GET /admin/analytics/files
```

#### 8. Chat Analytics
```http
GET /admin/analytics/chat
```

### Administrative Actions

#### 9. List Tenants (Admin)
```http
GET /admin/tenants
```

#### 10. Tenant Actions
```http
POST /admin/tenants/actions
```

**Request Body:**
```json
{
  "action": "activate",
  "tenant_id": "tenant-uuid",
  "parameters": {
    "max_users": 200
  },
  "reason": "Upgrade requested"
}
```

#### 11. List Users (Admin)
```http
GET /admin/users
```

#### 12. User Actions
```http
POST /admin/users/actions
```

**Request Body:**
```json
{
  "action": "deactivate",
  "user_id": "user-uuid",
  "reason": "Account violation"
}
```

#### 13. System Configuration
```http
GET /admin/config/system
PUT /admin/config/system
```

#### 14. System Actions
```http
POST /admin/actions/system
```

**Request Body:**
```json
{
  "action": "backup",
  "parameters": {
    "include_files": true
  },
  "scheduled_for": "2024-01-01T02:00:00Z"
}
```

#### 15. Export Tenant Data
```http
GET /admin/export/tenant-data/{tenant_id}
```

#### 16. Activity Logs
```http
GET /admin/logs/activity
```

**Query Parameters:**
- `page`: int (default: 1)
- `page_size`: int (default: 50)
- `action`: string (optional)
- `resource_type`: string (optional)
- `user_id`: string (optional)
- `date_from`: datetime (optional)
- `date_to`: datetime (optional)

---

## System Health

### Health Check Endpoint
```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "app_name": "Multi-Tenant RAG Chatbot", 
  "version": "1.0.0"
}
```

---

## Error Responses

### Standard Error Format
```json
{
  "detail": "Error message description",
  "error_code": "SPECIFIC_ERROR_CODE",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### Common HTTP Status Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 422 | Validation Error |
| 429 | Rate Limited |
| 500 | Internal Server Error |

### Authentication Errors
```json
{
  "detail": "Could not validate credentials",
  "error_code": "INVALID_TOKEN"
}
```

### Validation Errors
```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

---

## Rate Limiting

Default rate limits apply to all endpoints:

- **Standard Users**: 100 requests per minute
- **Admin Users**: 200 requests per minute
- **File Uploads**: 20 files per hour
- **Chat Endpoints**: 60 requests per minute

Rate limit headers included in responses:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640995200
```

---

## Integration Examples

### Python SDK Example
```python
import requests

# Authentication
auth_response = requests.post(
    "http://localhost:8000/api/v1/auth/login",
    json={"email": "user@example.com", "password": "password"}
)
token = auth_response.json()["access_token"]

# Headers for authenticated requests
headers = {"Authorization": f"Bearer {token}"}

# Create knowledge item
knowledge_response = requests.post(
    "http://localhost:8000/api/v1/knowledge/",
    json={
        "title": "API Usage Guide",
        "content": "This is how to use our API...",
        "document_type": "documentation"
    },
    headers=headers
)

# Send chat message
chat_response = requests.post(
    "http://localhost:8000/api/v1/chat/",
    json={
        "message": "How do I use the API?",
        "temperature": 0.7
    },
    headers=headers
)
```

### JavaScript/Node.js Example
```javascript
const axios = require('axios');

const BASE_URL = 'http://localhost:8000/api/v1';

// Login and get token
const auth = await axios.post(`${BASE_URL}/auth/login`, {
  email: 'user@example.com',
  password: 'password'
});

const token = auth.data.access_token;
const headers = { Authorization: `Bearer ${token}` };

// Upload file
const formData = new FormData();
formData.append('file', fileBuffer, 'document.pdf');
formData.append('auto_create_knowledge', 'true');

const uploadResponse = await axios.post(
  `${BASE_URL}/files/upload`,
  formData,
  { headers: { ...headers, 'Content-Type': 'multipart/form-data' } }
);

// Stream chat response
const chatStream = await axios.post(
  `${BASE_URL}/chat/stream`,
  { message: 'Tell me about the uploaded document' },
  { headers, responseType: 'stream' }
);
```

---

## API Testing

### Interactive Documentation
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

### Postman Collection
Import the API collection for Postman testing:
```bash
curl -o chatbot-api.postman_collection.json \
  http://localhost:8000/openapi.json
```

### Testing with cURL
```bash
# Login
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password"}'

# Chat (with token)
curl -X POST "http://localhost:8000/api/v1/chat/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello, can you help me?"}'
```

---

## Support & Contact

- **Documentation**: This file
- **API Status**: `GET /health`
- **Admin Dashboard**: `http://localhost:8000/admin` (admin access required)
- **OpenAPI Specification**: `http://localhost:8000/openapi.json`

For technical support or questions about the API, please contact the development team.

---

*Last Updated: December 2024*  
*API Version: 1.0.0*  
*Total Endpoints: 57* 