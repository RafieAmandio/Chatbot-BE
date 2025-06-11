#!/usr/bin/env python3
"""
Run script for Multi-Tenant RAG Chatbot Backend
"""

if __name__ == "__main__":
    import uvicorn
    from app.config import settings
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="debug" if settings.debug else "info"
    ) 