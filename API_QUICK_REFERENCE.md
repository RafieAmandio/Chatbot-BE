# Multi-Tenant RAG Chatbot - API Quick Reference

**Base URL**: `http://localhost:8000/api/v1`  
**Total Endpoints**: 57  
**Authentication**: Bearer JWT Token (except login/register)

---

## 🔐 Authentication (7 endpoints)
```
POST   /auth/register          - Register new user
POST   /auth/login             - User login
GET    /auth/me                - Get current user info
PUT    /auth/me                - Update user profile
POST   /auth/change-password   - Change password
POST   /auth/password-reset    - Request password reset
GET    /auth/verify-token      - Verify JWT token
```

## 💬 Chat & Conversations (4 endpoints)
```
POST   /chat/                     - Send chat message (non-streaming)
POST   /chat/stream               - Send chat message (streaming SSE)
POST   /chat/conversations        - Create new conversation
GET    /chat/conversations        - List user conversations
GET    /chat/conversations/{id}   - Get conversation with messages
```

## 🏢 Tenant Management (3 endpoints)
```
POST   /tenants/           - Create new tenant
GET    /tenants/           - List tenants
GET    /tenants/{id}       - Get tenant details
```

## 👥 User Management (3 endpoints)
```
POST   /auth/users         - Create user (admin)
GET    /users/             - List users
GET    /users/{id}         - Get user details
```

## 📚 Knowledge Management (7 endpoints)
```
POST   /knowledge/                  - Create knowledge item
GET    /knowledge/                  - List knowledge items
POST   /knowledge/search            - Search knowledge base
GET    /knowledge/types/list        - List document types
GET    /knowledge/{id}              - Get knowledge item
PUT    /knowledge/{id}              - Update knowledge item
DELETE /knowledge/{id}              - Delete knowledge item
```

## 🛍️ Product Management (8 endpoints)
```
POST   /products/                      - Create product
GET    /products/                      - List products
POST   /products/search                - Search products
GET    /products/categories/list       - List product categories
GET    /products/{id}                  - Get product details
PUT    /products/{id}                  - Update product
DELETE /products/{id}                  - Delete product
PUT    /products/{id}/stock            - Update stock quantity
```

## 🎯 Prompt Management (7 endpoints)
```
POST   /prompts/                       - Create prompt template
GET    /prompts/                       - List prompts
GET    /prompts/default/current        - Get current default prompt
POST   /prompts/test                   - Test prompt with message
GET    /prompts/{id}/variables         - Get prompt variables
POST   /prompts/{id}/set-default       - Set as default prompt
GET    /prompts/{id}                   - Get prompt details
PUT    /prompts/{id}                   - Update prompt
DELETE /prompts/{id}                   - Delete prompt
```

## 📁 File Upload System (8 endpoints)
```
POST   /files/upload                   - Upload single file
POST   /files/upload/bulk              - Upload multiple files (max 20)
GET    /files/                         - List uploaded files
GET    /files/stats/overview           - File system statistics
GET    /files/supported-formats        - List supported file formats
POST   /files/document/split           - Manual document chunking
GET    /files/{id}                     - Get file details
DELETE /files/{id}                     - Delete uploaded file
```

## 🛠️ Admin Dashboard (17 endpoints)

### System Overview
```
GET    /admin/dashboard                - Complete admin dashboard
GET    /admin/overview                 - System overview metrics
GET    /admin/health                   - System health check
```

### Analytics
```
GET    /admin/analytics/tenants        - Tenant usage analytics
GET    /admin/analytics/users          - User activity analytics
GET    /admin/analytics/knowledge      - Knowledge base analytics
GET    /admin/analytics/files          - File system analytics
GET    /admin/analytics/chat           - Chat interaction analytics
```

### Management
```
GET    /admin/tenants                  - List tenants with metrics
POST   /admin/tenants/actions          - Execute tenant actions
GET    /admin/users                    - List users with activity
POST   /admin/users/actions            - Execute user actions
```

### Configuration & Actions
```
GET    /admin/config/system            - Get system configuration
PUT    /admin/config/system            - Update system configuration
POST   /admin/actions/system           - Execute system actions
GET    /admin/export/tenant-data/{id}  - Export tenant data
GET    /admin/logs/activity            - Get activity logs
```

## ❤️ System Health (1 endpoint)
```
GET    /health                 - Basic health check
```

---

## 🔑 Authentication Required

All endpoints except the following require `Authorization: Bearer <token>`:
- `POST /auth/register`
- `POST /auth/login`
- `GET /health`

## 🛡️ Admin Access Required

The following endpoints require admin privileges:
- All `/admin/*` endpoints
- `POST /auth/users`

## 📝 Content Types

| Endpoint Type | Content-Type |
|---------------|--------------|
| JSON APIs | `application/json` |
| File Uploads | `multipart/form-data` |
| Streaming Chat | `text/event-stream` |

## 📊 Response Formats

| Operation | HTTP Status | Response |
|-----------|-------------|----------|
| Success | 200 | JSON data |
| Created | 201 | Created resource |
| No Content | 204 | Empty |
| Bad Request | 400 | Error details |
| Unauthorized | 401 | Auth error |
| Forbidden | 403 | Permission error |
| Not Found | 404 | Resource not found |
| Validation Error | 422 | Validation details |
| Server Error | 500 | Error message |

## 🚀 Quick Start

1. **Register & Login**:
   ```bash
   curl -X POST http://localhost:8000/api/v1/auth/register \
     -H "Content-Type: application/json" \
     -d '{"email":"user@test.com","password":"password123","name":"Test User","company_name":"Test Co"}'
   
   curl -X POST http://localhost:8000/api/v1/auth/login \
     -H "Content-Type: application/json" \
     -d '{"email":"user@test.com","password":"password123"}'
   ```

2. **Send Chat Message**:
   ```bash
   curl -X POST http://localhost:8000/api/v1/chat/ \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"message":"Hello, how can you help me?"}'
   ```

3. **Upload File**:
   ```bash
   curl -X POST http://localhost:8000/api/v1/files/upload \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -F "file=@document.pdf" \
     -F "auto_create_knowledge=true"
   ```

4. **Search Knowledge**:
   ```bash
   curl -X POST http://localhost:8000/api/v1/knowledge/search \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"query":"return policy","limit":5}'
   ```

---

## 📖 Full Documentation

For detailed request/response examples, see: `API_DOCUMENTATION.md`

## 🔧 Interactive Testing

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Spec**: http://localhost:8000/openapi.json

---

*API Version: 1.0.0 | Last Updated: December 2024* 