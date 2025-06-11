from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    # OpenAI Configuration
    openai_api_key: str
    openai_model: str = "gpt-4-turbo-preview"
    openai_embedding_model: str = "text-embedding-3-small"
    
    # Database Configuration
    database_url: str = "sqlite:///./chatbot.db"
    chroma_persist_directory: str = "./chroma_db"
    
    # Security
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Application Settings
    app_name: str = "Multi-Tenant RAG Chatbot"
    app_version: str = "1.0.0"
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Rate Limiting
    rate_limit_requests_per_minute: int = 100
    max_concurrent_requests: int = 10
    
    # OpenAI Rate Limiting
    openai_max_retries: int = 3
    openai_request_timeout: int = 60
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings() 