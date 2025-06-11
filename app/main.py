import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from sqlalchemy.exc import SQLAlchemyError

from app.config import settings
from app.database.connection import init_db
from app.api.chat import router as chat_router
from app.api.auth import router as auth_router
from app.api.tenants import router as tenants_router
from app.api.users import router as users_router
from app.api.knowledge import router as knowledge_router
from app.api.products import router as products_router
from app.api.prompts import router as prompts_router
from app.api.files import router as files_router
from app.api.admin import router as admin_router
from app.services.vector_store import vector_store

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.debug else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("Starting up Multi-Tenant RAG Chatbot Backend...")
    
    try:
        # Initialize database
        init_db()
        logger.info("Database initialized successfully")
        
        # Initialize vector store (already done in vector_store.py)
        logger.info("Vector store initialized successfully")
        
        # Create default tenant and admin user if needed
        await create_default_data()
        
        logger.info("Application startup completed")
        
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")


async def create_default_data():
    """Create default tenant and user if they don't exist"""
    try:
        from app.database.connection import SessionLocal
        from app.database.models import Tenant, User, Prompt
        from app.services.auth_service import auth_service
        
        db = SessionLocal()
        
        # Check if default tenant exists
        default_tenant = db.query(Tenant).filter(Tenant.domain == "default").first()
        
        if not default_tenant:
            # Create default tenant
            default_tenant = Tenant(
                name="Default Tenant",
                domain="default",
                description="Default tenant for testing and development"
            )
            db.add(default_tenant)
            db.commit()
            db.refresh(default_tenant)
            
            # Create default prompt
            default_prompt = Prompt(
                tenant_id=default_tenant.id,
                name="Default Customer Service Prompt",
                system_prompt="""You are a helpful customer service assistant. You have access to knowledge base and product information to help customers with their questions.

Use the available tools to search for relevant information when needed:
- search_knowledge: For general information and documentation
- search_products: For finding products
- get_product_details: For specific product information
- check_product_availability: For stock information

Always be helpful, accurate, and professional in your responses.""",
                description="Default system prompt for customer service chatbot",
                is_default=True
            )
            db.add(default_prompt)
            
            # Create default admin user using auth service
            admin_user = auth_service.create_user(
                db=db,
                email="admin@default.com",
                password="admin123",
                full_name="Default Admin",
                tenant_id=default_tenant.id,
                is_admin=True
            )
            
            db.commit()
            logger.info("Created default tenant, admin user, and prompt")
        
        db.close()
        
    except Exception as e:
        logger.error(f"Error creating default data: {e}")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Multi-Tenant RAG + Tooling Chatbot Backend with OpenAI integration",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add trusted host middleware for production
if not settings.debug:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"]  # Configure this properly for production
    )


# Exception handlers
@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request, exc):
    logger.error(f"Database error: {exc}")
    return HTTPException(
        status_code=500,
        detail="Database error occurred"
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unexpected error: {exc}")
    return HTTPException(
        status_code=500,
        detail="Internal server error"
    )


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "app_name": settings.app_name,
        "version": settings.app_version
    }


# Include routers
app.include_router(chat_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(tenants_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(knowledge_router, prefix="/api/v1")
app.include_router(products_router, prefix="/api/v1")
app.include_router(prompts_router, prefix="/api/v1")
app.include_router(files_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="debug" if settings.debug else "info"
    ) 