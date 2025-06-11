import os
import uuid
import time
import asyncio
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func
import logging

from app.database.connection import get_db
from app.database.models import UploadedFile, User, Tenant, KnowledgeItem
from app.schemas.file_upload import (
    FileUploadRequest, UploadedFileResponse, FileProcessingResult,
    BulkUploadRequest, BulkUploadResponse, FileSearchRequest, FileStatsResponse,
    DocumentSplitterRequest, DocumentSplitterResponse, ProcessingStatus
)
from app.auth.dependencies import get_current_user, get_current_tenant
from app.services.file_processor import file_processor
from app.services.document_splitter import document_splitter
from app.services.vector_store import vector_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/files", tags=["file-management"])


class FileUploadService:
    """Service for handling file uploads and processing"""
    
    async def process_uploaded_file(
        self,
        uploaded_file: UploadedFile,
        db: Session,
        auto_create_knowledge: bool = True,
        document_type: Optional[str] = None,
        custom_metadata: Optional[dict] = None
    ) -> FileProcessingResult:
        """Process an uploaded file and optionally create knowledge items"""
        start_time = time.time()
        
        try:
            # Update status to processing
            uploaded_file.processing_status = ProcessingStatus.PROCESSING
            db.commit()
            
            # Process the file
            result = await file_processor.process_file(
                uploaded_file.file_path,
                uploaded_file.original_filename
            )
            
            if not result["success"]:
                # Update status to failed
                uploaded_file.processing_status = ProcessingStatus.FAILED
                uploaded_file.processing_error = result["error"]
                db.commit()
                
                return FileProcessingResult(
                    file_id=uploaded_file.id,
                    filename=uploaded_file.original_filename,
                    success=False,
                    error=result["error"],
                    processing_time=time.time() - start_time
                )
            
            # Update file record with extracted text
            uploaded_file.extracted_text = result["text"]
            uploaded_file.extraction_metadata = result["metadata"]
            uploaded_file.processing_status = ProcessingStatus.COMPLETED
            uploaded_file.processed_at = func.now()
            
            knowledge_items_created = 0
            
            # Create knowledge items if requested
            if auto_create_knowledge and result["text"]:
                knowledge_items_created = await self._create_knowledge_items_from_text(
                    text=result["text"],
                    title=uploaded_file.original_filename,
                    source=uploaded_file.file_path,
                    document_type=document_type or uploaded_file.file_extension,
                    tenant_id=uploaded_file.tenant_id,
                    uploaded_file_id=uploaded_file.id,
                    custom_metadata=custom_metadata,
                    db=db
                )
            
            uploaded_file.knowledge_items_created = knowledge_items_created
            db.commit()
            
            processing_time = time.time() - start_time
            
            return FileProcessingResult(
                file_id=uploaded_file.id,
                filename=uploaded_file.original_filename,
                success=True,
                text_extracted=bool(result["text"]),
                text_length=len(result["text"]) if result["text"] else 0,
                word_count=result["metadata"].get("word_count", 0),
                knowledge_items_created=knowledge_items_created,
                processing_time=processing_time,
                metadata=result["metadata"]
            )
            
        except Exception as e:
            logger.error(f"Error processing file {uploaded_file.original_filename}: {e}")
            
            # Update status to failed
            uploaded_file.processing_status = ProcessingStatus.FAILED
            uploaded_file.processing_error = str(e)
            db.commit()
            
            return FileProcessingResult(
                file_id=uploaded_file.id,
                filename=uploaded_file.original_filename,
                success=False,
                error=str(e),
                processing_time=time.time() - start_time
            )
    
    async def _create_knowledge_items_from_text(
        self,
        text: str,
        title: str,
        source: str,
        document_type: str,
        tenant_id: str,
        uploaded_file_id: str,
        custom_metadata: Optional[dict],
        db: Session,
        max_chunk_size: int = 5000,
        chunk_overlap: int = 200
    ) -> int:
        """Create knowledge items from extracted text, splitting if necessary"""
        
        # Check if document needs splitting
        if len(text) > max_chunk_size:
            # Split into chunks
            chunks = document_splitter.split_document(
                content=text,
                title=title,
                max_chunk_size=max_chunk_size,
                chunk_overlap=chunk_overlap,
                source=source,
                document_type=document_type,
                metadata=custom_metadata
            )
            
            items_created = 0
            for chunk in chunks:
                knowledge_item = KnowledgeItem(
                    tenant_id=tenant_id,
                    title=chunk.title,
                    content=chunk.content,
                    source=source,
                    document_type=document_type,
                    meta_data=chunk.metadata,
                    uploaded_file_id=uploaded_file_id
                )
                
                db.add(knowledge_item)
                db.flush()  # Get the ID
                
                # Add to vector store
                try:
                    vector_id = await vector_store.add_knowledge_item(
                        knowledge_item.id,
                        chunk.title,
                        chunk.content,
                        tenant_id,
                        metadata=chunk.metadata
                    )
                    knowledge_item.vector_id = vector_id
                    items_created += 1
                except Exception as e:
                    logger.error(f"Error adding chunk to vector store: {e}")
            
            db.commit()
            return items_created
        
        else:
            # Create single knowledge item
            knowledge_item = KnowledgeItem(
                tenant_id=tenant_id,
                title=title,
                content=text,
                source=source,
                document_type=document_type,
                meta_data=custom_metadata,
                uploaded_file_id=uploaded_file_id
            )
            
            db.add(knowledge_item)
            db.flush()
            
            # Add to vector store
            try:
                vector_id = await vector_store.add_knowledge_item(
                    knowledge_item.id,
                    title,
                    text,
                    tenant_id,
                    metadata=custom_metadata
                )
                knowledge_item.vector_id = vector_id
                db.commit()
                return 1
            except Exception as e:
                logger.error(f"Error adding to vector store: {e}")
                db.commit()
                return 1  # Still created the knowledge item


file_upload_service = FileUploadService()


@router.post("/upload", response_model=UploadedFileResponse)
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    auto_create_knowledge: bool = Form(True),
    document_type: Optional[str] = Form(None),
    custom_metadata: Optional[str] = Form(None),  # JSON string
    current_tenant: Tenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload a single file for processing"""
    
    # Read file content
    file_content = await file.read()
    
    # Validate file
    validation = file_processor.validate_file(
        file_content, file.filename, file.content_type
    )
    
    if not validation["valid"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File validation failed: {', '.join(validation['errors'])}"
        )
    
    try:
        # Save file to disk
        file_path = await file_processor.save_file(
            file_content, file.filename, current_tenant.id
        )
        
        # Parse custom metadata
        metadata = None
        if custom_metadata:
            try:
                import json
                metadata = json.loads(custom_metadata)
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON in custom_metadata: {custom_metadata}")
        
        # Create database record
        uploaded_file = UploadedFile(
            tenant_id=current_tenant.id,
            uploaded_by_id=current_user.id,
            original_filename=file.filename,
            file_path=file_path,
            file_size=len(file_content),
            content_type=file.content_type,
            file_extension=os.path.splitext(file.filename)[1].lower().lstrip('.'),
            auto_create_knowledge=auto_create_knowledge
        )
        
        db.add(uploaded_file)
        db.commit()
        db.refresh(uploaded_file)
        
        # Process file in background
        background_tasks.add_task(
            file_upload_service.process_uploaded_file,
            uploaded_file,
            db,
            auto_create_knowledge,
            document_type,
            metadata
        )
        
        logger.info(f"File uploaded: {file.filename} by {current_user.email}")
        return uploaded_file
        
    except Exception as e:
        logger.error(f"Error uploading file {file.filename}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"File upload failed: {str(e)}"
        )


@router.post("/upload/bulk", response_model=BulkUploadResponse)
async def upload_bulk_files(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    bulk_request: BulkUploadRequest = Depends(),
    current_tenant: Tenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload multiple files for batch processing"""
    
    if len(files) > 20:  # Limit bulk uploads
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 20 files allowed per bulk upload"
        )
    
    batch_id = str(uuid.uuid4())
    start_time = time.time()
    results = []
    successful_uploads = 0
    failed_uploads = 0
    
    for file in files:
        try:
            # Read and validate file
            file_content = await file.read()
            validation = file_processor.validate_file(
                file_content, file.filename, file.content_type
            )
            
            if not validation["valid"]:
                results.append(FileProcessingResult(
                    file_id="",
                    filename=file.filename,
                    success=False,
                    error=f"Validation failed: {', '.join(validation['errors'])}"
                ))
                failed_uploads += 1
                continue
            
            # Save file
            file_path = await file_processor.save_file(
                file_content, file.filename, current_tenant.id
            )
            
            # Create database record
            uploaded_file = UploadedFile(
                tenant_id=current_tenant.id,
                uploaded_by_id=current_user.id,
                original_filename=file.filename,
                file_path=file_path,
                file_size=len(file_content),
                content_type=file.content_type,
                file_extension=os.path.splitext(file.filename)[1].lower().lstrip('.'),
                auto_create_knowledge=bulk_request.auto_create_knowledge
            )
            
            db.add(uploaded_file)
            db.flush()
            
            # Process file immediately for bulk operations
            result = await file_upload_service.process_uploaded_file(
                uploaded_file,
                db,
                bulk_request.auto_create_knowledge,
                bulk_request.default_document_type
            )
            
            results.append(result)
            
            if result.success:
                successful_uploads += 1
            else:
                failed_uploads += 1
                
        except Exception as e:
            logger.error(f"Error in bulk upload for {file.filename}: {e}")
            results.append(FileProcessingResult(
                file_id="",
                filename=file.filename,
                success=False,
                error=str(e)
            ))
            failed_uploads += 1
    
    db.commit()
    
    # Calculate total knowledge items created
    total_knowledge_items = sum(r.knowledge_items_created for r in results if r.success)
    
    logger.info(f"Bulk upload completed: {successful_uploads} successful, {failed_uploads} failed")
    
    return BulkUploadResponse(
        batch_id=batch_id,
        total_files=len(files),
        successful_uploads=successful_uploads,
        failed_uploads=failed_uploads,
        processing_status=ProcessingStatus.COMPLETED,
        results=results,
        total_knowledge_items_created=total_knowledge_items,
        processing_time=time.time() - start_time
    )


@router.get("/", response_model=List[UploadedFileResponse])
async def list_uploaded_files(
    skip: int = 0,
    limit: int = 100,
    processing_status: Optional[ProcessingStatus] = None,
    file_extension: Optional[str] = None,
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """List uploaded files for tenant"""
    query = db.query(UploadedFile).filter(
        UploadedFile.tenant_id == current_tenant.id,
        UploadedFile.is_active == True
    )
    
    if processing_status:
        query = query.filter(UploadedFile.processing_status == processing_status)
    
    if file_extension:
        query = query.filter(UploadedFile.file_extension == file_extension)
    
    files = query.order_by(UploadedFile.created_at.desc()).offset(skip).limit(limit).all()
    return files


@router.get("/{file_id}", response_model=UploadedFileResponse)
async def get_uploaded_file(
    file_id: str,
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Get specific uploaded file details"""
    uploaded_file = db.query(UploadedFile).filter(
        UploadedFile.id == file_id,
        UploadedFile.tenant_id == current_tenant.id
    ).first()
    
    if not uploaded_file:
        raise HTTPException(status_code=404, detail="File not found")
    
    return uploaded_file


@router.delete("/{file_id}")
async def delete_uploaded_file(
    file_id: str,
    current_tenant: Tenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete uploaded file and associated knowledge items"""
    uploaded_file = db.query(UploadedFile).filter(
        UploadedFile.id == file_id,
        UploadedFile.tenant_id == current_tenant.id
    ).first()
    
    if not uploaded_file:
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        # Delete physical file
        await file_processor.delete_file(uploaded_file.file_path)
        
        # Soft delete database record
        uploaded_file.is_active = False
        
        # Optionally delete associated knowledge items
        db.query(KnowledgeItem).filter(
            KnowledgeItem.uploaded_file_id == file_id
        ).update({"is_active": False})
        
        db.commit()
        
        logger.info(f"File deleted: {uploaded_file.original_filename} by {current_user.email}")
        return {"message": "File deleted successfully"}
        
    except Exception as e:
        logger.error(f"Error deleting file {file_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete file: {str(e)}"
        )


@router.get("/stats/overview", response_model=FileStatsResponse)
async def get_file_stats(
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Get file upload statistics for tenant"""
    
    # Total files and size
    stats_query = db.query(
        func.count(UploadedFile.id).label('total_files'),
        func.sum(UploadedFile.file_size).label('total_size')
    ).filter(
        UploadedFile.tenant_id == current_tenant.id,
        UploadedFile.is_active == True
    ).first()
    
    # Processing status counts
    status_counts = {}
    for status in ProcessingStatus:
        count = db.query(UploadedFile).filter(
            UploadedFile.tenant_id == current_tenant.id,
            UploadedFile.processing_status == status,
            UploadedFile.is_active == True
        ).count()
        status_counts[status] = count
    
    # File type counts
    type_counts = {}
    type_results = db.query(
        UploadedFile.file_extension,
        func.count(UploadedFile.id).label('count')
    ).filter(
        UploadedFile.tenant_id == current_tenant.id,
        UploadedFile.is_active == True
    ).group_by(UploadedFile.file_extension).all()
    
    for ext, count in type_results:
        type_counts[ext or 'unknown'] = count
    
    # Knowledge items created
    knowledge_items_created = db.query(
        func.sum(UploadedFile.knowledge_items_created)
    ).filter(
        UploadedFile.tenant_id == current_tenant.id,
        UploadedFile.is_active == True
    ).scalar() or 0
    
    return FileStatsResponse(
        total_files=stats_query.total_files or 0,
        total_size=stats_query.total_size or 0,
        processing_status_counts=status_counts,
        file_type_counts=type_counts,
        knowledge_items_created=knowledge_items_created,
        storage_usage={
            "total_size": stats_query.total_size or 0,
            "average_file_size": (stats_query.total_size or 0) // max(stats_query.total_files or 1, 1)
        }
    )


@router.post("/document/split", response_model=DocumentSplitterResponse)
async def split_document(
    request: DocumentSplitterRequest,
    current_tenant: Tenant = Depends(get_current_tenant)
):
    """Split a document into optimized chunks"""
    
    chunks = document_splitter.split_document(
        content=request.content,
        title=request.title,
        max_chunk_size=request.max_chunk_size,
        chunk_overlap=request.chunk_overlap,
        preserve_structure=request.preserve_structure,
        source=request.source,
        document_type=request.document_type,
        metadata=request.metadata
    )
    
    return DocumentSplitterResponse(
        chunks=chunks,
        total_chunks=len(chunks),
        original_length=len(request.content),
        total_chunks_length=sum(len(chunk.content) for chunk in chunks)
    )


@router.get("/supported-formats")
async def get_supported_formats():
    """Get list of supported file formats"""
    return {
        "formats": file_processor.SUPPORTED_FORMATS,
        "max_file_size": file_processor.MAX_FILE_SIZE,
        "max_bulk_files": 20
    } 