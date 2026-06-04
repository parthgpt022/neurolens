"""
backend/app/routers/documents.py

Document management endpoints:
  POST /api/documents/upload     — upload a PDF/image
  GET  /api/documents            — list user's documents
  GET  /api/documents/{id}       — document detail + extracted text
  GET  /api/documents/{id}/entities — structured entities (amounts, dates, etc.)
  DELETE /api/documents/{id}     — delete document + its vectors
"""

import uuid
import asyncio
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger

from app.core.database import get_db
from app.core.config import get_settings
from app.models.db_models import User, Document, DocumentStatus, ExtractedEntity
from app.models.schemas import DocumentResponse, DocumentDetailResponse, EntityResponse
from app.services.auth_service import get_current_user
from app.services.document_service import get_document_service

router = APIRouter(prefix="/api/documents", tags=["documents"])
settings = get_settings()

ALLOWED_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/tiff",
    "image/webp",
}
MAX_FILE_SIZE_MB = 50


@router.post("/upload", response_model=DocumentResponse, status_code=202)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a document for processing.
    Returns immediately (202 Accepted) — processing happens in the background.
    Poll GET /api/documents/{id} or use WebSocket /ws/processing/{id} for status.
    """
    # Validate file type
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type: {file.content_type}. Allowed: PDF, PNG, JPEG, TIFF, WebP",
        )

    # Read and check size
    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        raise HTTPException(
            status_code=413,
            detail=f"File too large: {size_mb:.1f}MB. Max: {MAX_FILE_SIZE_MB}MB",
        )

    # Create DB record
    doc_id = uuid.uuid4()
    safe_filename = file.filename.replace(" ", "_")
    storage_key = f"raw/{current_user.id}/{doc_id}/{safe_filename}"

    doc = Document(
        id=doc_id,
        user_id=current_user.id,
        filename=safe_filename,
        original_filename=file.filename,
        storage_key=storage_key,
        file_size_bytes=len(content),
        mime_type=file.content_type,
        status=DocumentStatus.PENDING,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    # Upload to MinIO
    try:
        await _upload_to_minio(content, storage_key, file.content_type)
    except Exception as e:
        doc.status = DocumentStatus.FAILED
        doc.error_message = f"Storage upload failed: {str(e)}"
        await db.commit()
        raise HTTPException(status_code=500, detail="Failed to store document")

    # Kick off background processing
    background_tasks.add_task(
        _run_processing,
        doc_id=doc_id,
        storage_key=storage_key,
    )

    logger.info(f"Document {doc_id} queued for processing by user {current_user.id}")
    return DocumentResponse.model_validate(doc)


@router.get("", response_model=list[DocumentResponse])
async def list_documents(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Document)
        .where(Document.user_id == current_user.id)
        .order_by(Document.created_at.desc())
    )
    docs = result.scalars().all()
    return [DocumentResponse.model_validate(d) for d in docs]


@router.get("/{doc_id}", response_model=DocumentDetailResponse)
async def get_document(
    doc_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = await _get_owned_doc(doc_id, current_user.id, db)
    return DocumentDetailResponse.model_validate(doc)


@router.get("/{doc_id}/entities", response_model=list[EntityResponse])
async def get_entities(
    doc_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_owned_doc(doc_id, current_user.id, db)  # ownership check
    result = await db.execute(
        select(ExtractedEntity)
        .where(ExtractedEntity.document_id == doc_id)
        .order_by(ExtractedEntity.page_number, ExtractedEntity.entity_type)
    )
    entities = result.scalars().all()
    return [EntityResponse.model_validate(e) for e in entities]


@router.delete("/{doc_id}", status_code=204)
async def delete_document(
    doc_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = await _get_owned_doc(doc_id, current_user.id, db)

    # Delete vectors from ChromaDB
    try:
        import chromadb
        client = chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port)
        collection = client.get_collection(settings.chroma_collection)
        # Delete all chunks belonging to this document
        collection.delete(where={"document_id": str(doc_id)})
    except Exception as e:
        logger.warning(f"ChromaDB delete failed for {doc_id}: {e}")

    await db.delete(doc)
    await db.commit()


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_owned_doc(
    doc_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession
) -> Document:
    result = await db.execute(
        select(Document).where(
            Document.id == doc_id, Document.user_id == user_id
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


async def _upload_to_minio(
    content: bytes, storage_key: str, content_type: str
) -> None:
    import io
    from minio import Minio
    client = Minio(
        settings.minio_endpoint,
        access_key=settings.minio_root_user,
        secret_key=settings.minio_root_password,
        secure=False,
    )
    # Create bucket if it doesn't exist
    if not client.bucket_exists(settings.minio_bucket):
        client.make_bucket(settings.minio_bucket)

    client.put_object(
        bucket_name=settings.minio_bucket,
        object_name=storage_key,
        data=io.BytesIO(content),
        length=len(content),
        content_type=content_type,
    )


async def _run_processing(doc_id: uuid.UUID, storage_key: str) -> None:
    """Background task — runs the full processing pipeline."""
    from app.core.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        try:
            service = get_document_service()
            await service.process_document(
                document_id=doc_id,
                storage_key=storage_key,
                db_session=db,
            )
        except Exception as e:
            logger.error(f"Background processing failed for {doc_id}: {e}")
