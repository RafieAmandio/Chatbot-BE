from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.connection import Base
import uuid


class Tenant(Base):
    __tablename__ = "tenants"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    domain = Column(String(255), unique=True, nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Configuration
    max_users = Column(Integer, default=100)
    max_documents = Column(Integer, default=1000)
    max_products = Column(Integer, default=1000)
    
    # Relationships
    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    knowledge_items = relationship("KnowledgeItem", back_populates="tenant", cascade="all, delete-orphan")
    products = relationship("Product", back_populates="tenant", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="tenant", cascade="all, delete-orphan")
    prompts = relationship("Prompt", back_populates="tenant", cascade="all, delete-orphan")
    tools = relationship("Tool", back_populates="tenant", cascade="all, delete-orphan")
    uploaded_files = relationship("UploadedFile", back_populates="tenant", cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    email = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    tenant = relationship("Tenant", back_populates="users")
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    uploaded_files = relationship("UploadedFile", back_populates="uploaded_by", cascade="all, delete-orphan")


class KnowledgeItem(Base):
    __tablename__ = "knowledge_items"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    source = Column(String(500))  # file path, URL, etc.
    document_type = Column(String(50))  # pdf, txt, html, etc.
    meta_data = Column(JSON)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Vector store reference
    vector_id = Column(String(255))  # ChromaDB document ID
    
    # File upload reference
    uploaded_file_id = Column(String, ForeignKey("uploaded_files.id"), nullable=True)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="knowledge_items")
    uploaded_file = relationship("UploadedFile", back_populates="knowledge_items")


class Product(Base):
    __tablename__ = "products"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    name = Column(String(500), nullable=False)
    description = Column(Text)
    category = Column(String(255))
    price = Column(Float)
    currency = Column(String(10), default="USD")
    sku = Column(String(255))
    stock_quantity = Column(Integer, default=0)
    specifications = Column(JSON)
    meta_data = Column(JSON)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Vector store reference
    vector_id = Column(String(255))  # ChromaDB document ID
    
    # Relationships
    tenant = relationship("Tenant", back_populates="products")


class UploadedFile(Base):
    __tablename__ = "uploaded_files"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    uploaded_by_id = Column(String, ForeignKey("users.id"), nullable=False)
    original_filename = Column(String(500), nullable=False)
    file_path = Column(String(1000), nullable=False)
    file_size = Column(Integer, nullable=False)
    content_type = Column(String(255))
    file_extension = Column(String(10))
    
    # Processing status
    processing_status = Column(String(50), default="pending")  # pending, processing, completed, failed
    processing_error = Column(Text)
    processed_at = Column(DateTime(timezone=True))
    
    # Text extraction results
    extracted_text = Column(Text)
    extraction_metadata = Column(JSON)
    
    # Knowledge base integration
    auto_create_knowledge = Column(Boolean, default=True)
    knowledge_items_created = Column(Integer, default=0)
    
    # File metadata
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    tenant = relationship("Tenant", back_populates="uploaded_files")
    uploaded_by = relationship("User", back_populates="uploaded_files")
    knowledge_items = relationship("KnowledgeItem", back_populates="uploaded_file", cascade="all, delete-orphan")


class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    title = Column(String(500))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    tenant = relationship("Tenant", back_populates="conversations")
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=False)
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    meta_data = Column(JSON)  # tool calls, function results, etc.
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")


class Prompt(Base):
    __tablename__ = "prompts"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    name = Column(String(255), nullable=False)
    system_prompt = Column(Text, nullable=False)
    description = Column(Text)
    variables = Column(JSON)  # Template variables and their default values
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    tenant = relationship("Tenant", back_populates="prompts")


class Tool(Base):
    __tablename__ = "tools"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    function_schema = Column(JSON, nullable=False)  # OpenAI function schema
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    tenant = relationship("Tenant", back_populates="tools") 