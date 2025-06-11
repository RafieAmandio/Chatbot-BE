# Multi-Tenant RAG Chatbot Backend

A comprehensive **Multi-Tenant RAG (Retrieval-Augmented Generation) Chatbot Backend** built with FastAPI, featuring OpenAI integration, vector-based knowledge retrieval, file processing capabilities, and administrative dashboard.

[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104.1-green.svg)](https://fastapi.tiangolo.com)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4-orange.svg)](https://openai.com)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-0.4.15-purple.svg)](https://www.trychroma.com)

## 🚀 Features

### 🔐 **Multi-Tenant Authentication System**
- JWT-based authentication with secure password hashing
- Role-based access control (Admin/User)
- Tenant isolation and data security
- Password reset and profile management

### 💬 **Advanced Chat System**
- **Streaming & Non-streaming responses** via OpenAI GPT-4
- **Conversation management** with persistent chat history
- **Tool integration** for knowledge search and product queries
- **Context-aware responses** using conversation history

### 📚 **Knowledge Management**
- **Vector-based knowledge base** using ChromaDB
- **Semantic search** with similarity scoring
- **Document categorization** and metadata management
- **Automatic knowledge item creation** from uploaded files

### 🛍️ **Product Management**
- **Product catalog** with categories and specifications
- **Inventory tracking** with stock management
- **Vector-based product search** for intelligent recommendations
- **Dynamic pricing** and product metadata

### 🎯 **Prompt Engineering System**
- **Dynamic prompt templates** with variable substitution
- **A/B testing** for prompt optimization
- **Default prompt management** per tenant
- **Prompt performance testing**

### 📁 **Advanced File Processing**
- **Multi-format support**: PDF, DOCX, Excel, CSV, TXT, HTML, JSON, XML, Markdown
- **Intelligent document splitting** with context preservation
- **Bulk file upload** (up to 20 files simultaneously)
- **Background processing** with status tracking
- **Automatic knowledge base integration**

### 🛠️ **Admin Dashboard**
- **System monitoring** with real-time health checks
- **Analytics & reporting** for tenants, users, and usage
- **Tenant & user management** with administrative actions
- **File system analytics** and storage monitoring
- **Activity logging** and audit trails

### ⚡ **Technical Features**
- **Asynchronous processing** with FastAPI
- **Vector store optimization** with ChromaDB
- **Automatic scaling** and tenant isolation
- **Comprehensive error handling** and logging
- **RESTful API design** with OpenAPI documentation
- **Production-ready** with Docker support

---

## 📊 System Overview

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Web Frontend  │───▶│  FastAPI Backend │───▶│   OpenAI API    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌──────────────────┐    ┌─────────────────┐
                       │   SQLite DB      │    │   ChromaDB      │
                       │   (Metadata)     │    │   (Vectors)     │
                       └──────────────────┘    └─────────────────┘
```

**Architecture Components:**
- **FastAPI Backend**: 57 REST API endpoints
- **SQLite Database**: User data, conversations, metadata
- **ChromaDB Vector Store**: Knowledge embeddings and similarity search
- **OpenAI Integration**: GPT-4 for chat responses and embeddings
- **File Processing Pipeline**: Multi-format document processing
- **Admin Dashboard**: Real-time monitoring and management

---

## 🏗️ Project Structure

```
CS-Chatbot-BE/
├── app/
│   ├── api/                  # API endpoints (57 total)
│   │   ├── auth.py          # Authentication (8 endpoints)
│   │   ├── chat.py          # Chat & conversations (5 endpoints)
│   │   ├── tenants.py       # Tenant management (7 endpoints)
│   │   ├── users.py         # User management (7 endpoints)
│   │   ├── knowledge.py     # Knowledge base (5 endpoints)
│   │   ├── products.py      # Product catalog (5 endpoints)
│   │   ├── prompts.py       # Prompt templates (6 endpoints)
│   │   ├── files.py         # File uploads (8 endpoints)
│   │   └── admin.py         # Admin dashboard (16 endpoints)
│   ├── auth/                # Authentication & middleware
│   ├── database/            # Database models & connection
│   ├── schemas/             # Pydantic models
│   ├── services/            # Business logic services
│   ├── config.py           # Configuration settings
│   └── main.py             # FastAPI application
├── data/                   # ChromaDB storage
├── uploads/               # File upload storage
├── API_DOCUMENTATION.md   # Complete API documentation
├── API_QUICK_REFERENCE.md # Quick reference guide
└── requirements.txt       # Python dependencies
```

---

## ⚡ Quick Start

### 1. Clone Repository
```bash
git clone <repository-url>
cd CS-Chatbot-BE
```

### 2. Environment Setup
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration
Create `.env` file:
```env
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Database
DATABASE_URL=sqlite:///./chatbot.db

# JWT Secret
SECRET_KEY=your_secret_key_here

# App Settings
DEBUG=true
HOST=0.0.0.0
PORT=8000
APP_NAME="Multi-Tenant RAG Chatbot"
APP_VERSION="1.0.0"

# ChromaDB
CHROMA_PERSIST_DIRECTORY=./data/chroma_db
```

### 4. Run Application
```bash
# Development server
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Production server
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 5. Access Services
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Admin Dashboard**: http://localhost:8000/admin (admin access required)

---

## 📖 API Documentation

### Quick Reference (57 Endpoints)

| Category | Endpoints | Description |
|----------|-----------|-------------|
| 🔐 **Authentication** | 8 | User registration, login, profile management |
| 💬 **Chat** | 5 | Streaming/non-streaming chat, conversations |
| 🏢 **Tenants** | 7 | Multi-tenant management |
| 👥 **Users** | 7 | User management and administration |
| 📚 **Knowledge** | 5 | Knowledge base and semantic search |
| 🛍️ **Products** | 5 | Product catalog and inventory |
| 🎯 **Prompts** | 6 | Prompt templates and testing |
| 📁 **Files** | 8 | File upload and processing |
| 🛠️ **Admin** | 16 | System monitoring and management |

### Complete Documentation
- **[Full API Documentation](API_DOCUMENTATION.md)** - Detailed request/response examples
- **[Quick Reference Guide](API_QUICK_REFERENCE.md)** - Compact endpoint listing
- **Interactive Docs**: http://localhost:8000/docs (Swagger UI)
- **ReDoc**: http://localhost:8000/redoc

---

## 🔧 Usage Examples

### Authentication
```python
import requests

# Register user
response = requests.post("http://localhost:8000/api/v1/auth/register", json={
    "email": "user@example.com",
    "password": "securepass123",
    "name": "John Doe",
    "company_name": "Example Corp"
})

# Login
auth = requests.post("http://localhost:8000/api/v1/auth/login", json={
    "email": "user@example.com",
    "password": "securepass123"
})
token = auth.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}
```

### Chat Interaction
```python
# Send chat message
chat_response = requests.post(
    "http://localhost:8000/api/v1/chat/",
    headers=headers,
    json={
        "message": "What's your return policy?",
        "temperature": 0.7
    }
)

# Stream chat response
stream_response = requests.post(
    "http://localhost:8000/api/v1/chat/stream",
    headers=headers,
    json={"message": "Tell me about your products"},
    stream=True
)
```

### File Upload
```python
# Upload PDF document
with open("document.pdf", "rb") as f:
    files = {"file": f}
    upload_response = requests.post(
        "http://localhost:8000/api/v1/files/upload",
        headers=headers,
        files=files,
        data={"auto_create_knowledge": "true"}
    )
```

### Knowledge Search
```python
# Search knowledge base
search_response = requests.post(
    "http://localhost:8000/api/v1/knowledge/search",
    headers=headers,
    json={
        "query": "shipping policy",
        "limit": 10,
        "min_score": 0.7
    }
)
```

---

## 🛠️ Development

### Project Phases Completed

1. **✅ Phase 1: Authentication System**
   - JWT authentication, user management, tenant isolation

2. **✅ Phase 2: Management APIs**
   - Knowledge, products, prompts, comprehensive CRUD operations

3. **✅ Phase 3: File Upload System**
   - Multi-format processing, background tasks, vector integration

4. **✅ Phase 4: Admin Dashboard**
   - System monitoring, analytics, administrative controls

### Technology Stack
- **Backend**: FastAPI 0.104.1, Python 3.12+
- **Database**: SQLite with SQLAlchemy ORM
- **Vector Store**: ChromaDB 0.4.15
- **AI Integration**: OpenAI GPT-4, text-embedding-ada-002
- **Authentication**: JWT with bcrypt password hashing
- **File Processing**: PyPDF2, python-docx, pandas, openpyxl
- **Testing**: pytest, pytest-asyncio

### Key Dependencies
```
fastapi==0.104.1          # Web framework
openai==1.3.5             # AI integration
chromadb==0.4.15          # Vector database
sqlalchemy==2.0.23        # ORM
pydantic==2.4.2           # Data validation
python-jose==3.3.0        # JWT handling
passlib==1.7.4            # Password hashing
psutil==5.9.6             # System monitoring
```

---

## 🚦 Testing

### Run Tests
```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_auth.py
```

### Test Admin Dashboard
```bash
# Run admin dashboard tests
python test_admin_dashboard.py
```

### Manual Testing
```bash
# Test health endpoint
curl http://localhost:8000/health

# Test authentication
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@default.com","password":"admin123"}'
```

---

## 📦 Deployment

### Docker (Coming Soon)
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Production Considerations
- **Environment Variables**: Use production-ready secrets
- **Database**: Consider PostgreSQL for production
- **Reverse Proxy**: Nginx for SSL termination and load balancing
- **Monitoring**: Implement proper logging and monitoring
- **Backup**: Regular database and vector store backups

---

## 🔒 Security

- **JWT Authentication** with secure token handling
- **Password Hashing** using bcrypt
- **Tenant Isolation** with proper data access controls
- **Input Validation** using Pydantic models
- **Rate Limiting** on API endpoints
- **CORS Configuration** for cross-origin requests

---

## 📈 Monitoring & Analytics

### Admin Dashboard Features
- **System Overview**: Real-time metrics and health status
- **Tenant Analytics**: Usage patterns and resource consumption
- **User Activity**: Login patterns and engagement metrics
- **File Processing**: Upload statistics and processing times
- **Chat Analytics**: Conversation metrics and tool usage
- **System Health**: Database, vector store, and API health

### Health Check Endpoints
```bash
# Basic health check
GET /health

# Detailed system health (admin only)
GET /admin/health
```

---

## 🤝 Contributing

1. **Fork the repository**
2. **Create feature branch**: `git checkout -b feature/new-feature`
3. **Commit changes**: `git commit -am 'Add new feature'`
4. **Push to branch**: `git push origin feature/new-feature`
5. **Submit pull request**

### Development Guidelines
- Follow PEP 8 coding standards
- Add tests for new features
- Update documentation
- Ensure all tests pass

---

## 📞 Support

- **Documentation**: See `API_DOCUMENTATION.md` and `API_QUICK_REFERENCE.md`
- **Issues**: GitHub Issues for bug reports and feature requests
- **API Status**: `GET /health` for system status
- **Interactive Docs**: http://localhost:8000/docs

---

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## 🙏 Acknowledgments

- **FastAPI** for the excellent web framework
- **OpenAI** for GPT-4 and embedding capabilities
- **ChromaDB** for vector storage and similarity search
- **Pydantic** for data validation and serialization

---

**Multi-Tenant RAG Chatbot Backend v1.0.0**  
*Built with ❤️ using FastAPI, OpenAI, and ChromaDB*

---

*Last Updated: December 2024* 