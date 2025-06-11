from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class ProcessingStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class FileUploadRequest(BaseModel):
    auto_create_knowledge: Optional[bool] = True
    document_type: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    custom_metadata: Optional[Dict[str, Any]] = None


class UploadedFileResponse(BaseModel):
    id: str
    tenant_id: str
    uploaded_by_id: str
    original_filename: str
    file_size: int
    content_type: Optional[str]
    file_extension: Optional[str]
    processing_status: ProcessingStatus
    processing_error: Optional[str]
    processed_at: Optional[datetime]
    extraction_metadata: Optional[Dict[str, Any]]
    auto_create_knowledge: bool
    knowledge_items_created: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class FileProcessingResult(BaseModel):
    file_id: str
    filename: str
    success: bool
    error: Optional[str] = None
    text_extracted: bool = False
    text_length: Optional[int] = None
    word_count: Optional[int] = None
    knowledge_items_created: int = 0
    processing_time: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


class BulkUploadRequest(BaseModel):
    auto_create_knowledge: Optional[bool] = True
    default_document_type: Optional[str] = None
    default_category: Optional[str] = None
    split_large_documents: Optional[bool] = True
    max_chunk_size: Optional[int] = 5000
    chunk_overlap: Optional[int] = 200


class BulkUploadResponse(BaseModel):
    batch_id: str
    total_files: int
    successful_uploads: int
    failed_uploads: int
    processing_status: ProcessingStatus
    results: List[FileProcessingResult]
    total_knowledge_items_created: int
    processing_time: Optional[float] = None


class FileChunkRequest(BaseModel):
    text: str
    max_chunk_size: int = 5000
    overlap: int = 200
    preserve_paragraphs: bool = True


class FileChunkResponse(BaseModel):
    chunks: List[Dict[str, Any]]
    total_chunks: int
    total_characters: int


class FileSearchRequest(BaseModel):
    filename: Optional[str] = None
    processing_status: Optional[ProcessingStatus] = None
    file_extension: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    uploaded_by: Optional[str] = None


class FileStatsResponse(BaseModel):
    total_files: int
    total_size: int
    processing_status_counts: Dict[ProcessingStatus, int]
    file_type_counts: Dict[str, int]
    knowledge_items_created: int
    storage_usage: Dict[str, Any]


class DocumentSplitterRequest(BaseModel):
    content: str
    title: str
    source: Optional[str] = None
    document_type: Optional[str] = None
    max_chunk_size: int = Field(default=5000, ge=500, le=10000)
    chunk_overlap: int = Field(default=200, ge=0, le=1000)
    preserve_structure: bool = True
    metadata: Optional[Dict[str, Any]] = None


class DocumentChunk(BaseModel):
    title: str
    content: str
    chunk_index: int
    total_chunks: int
    source: Optional[str]
    document_type: Optional[str]
    metadata: Optional[Dict[str, Any]]


class DocumentSplitterResponse(BaseModel):
    chunks: List[DocumentChunk]
    total_chunks: int
    original_length: int
    total_chunks_length: int 