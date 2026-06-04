"""
backend/app/services/document_service.py

Orchestrates the full document processing pipeline:
  1. Retrieve file from MinIO
  2. Convert PDF pages to images
  3. Run OCR (NPU-accelerated)
  4. Chunk the extracted text
  5. Embed chunks (NPU-accelerated)
  6. Store in ChromaDB for RAG
  7. Update document status in Postgres

This runs as a background task so the upload endpoint returns immediately
and the user gets real-time updates via WebSocket.
"""

import sys
import uuid
import time
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional
from loguru import logger

# We'll resolve the npu_engine path dynamically
import os
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))


class DocumentService:
    """
    Handles the full document → OCR → embed → store pipeline.
    Initialized once and reused across requests (heavy models stay loaded).
    """

    def __init__(self):
        self._ocr = None        # Lazy-loaded on first use
        self._embedder = None   # Lazy-loaded on first use
        self._chroma = None     # Lazy-loaded on first use

    # ── Lazy loaders ─────────────────────────────────────────────────────────

    def _get_ocr(self):
        if self._ocr is None:
            from npu_engine.inference.ocr_runner import OCRRunner
            self._ocr = OCRRunner.get_instance()
        return self._ocr

    def _get_embedder(self):
        if self._embedder is None:
            from npu_engine.inference.embedding_runner import EmbeddingRunner
            self._embedder = EmbeddingRunner.get_instance()
        return self._embedder

    def _get_chroma(self):
        if self._chroma is None:
            import chromadb
            from app.core.config import get_settings
            settings = get_settings()
            client = chromadb.HttpClient(
                host=settings.chroma_host,
                port=settings.chroma_port,
            )
            self._chroma = client.get_or_create_collection(
                name=settings.chroma_collection,
                metadata={"hnsw:space": "cosine"},
            )
        return self._chroma

    # ── Main pipeline ─────────────────────────────────────────────────────────

    async def process_document(
        self,
        document_id: uuid.UUID,
        storage_key: str,
        db_session,
        progress_callback=None,
    ) -> dict:
        """
        Full processing pipeline. Returns OCR metadata dict.
        Updates document status in DB throughout.
        """
        from app.models.db_models import Document, DocumentStatus
        from sqlalchemy import select

        async def update_status(status: DocumentStatus, step: str, progress: int):
            result = await db_session.execute(
                select(Document).where(Document.id == document_id)
            )
            doc = result.scalar_one_or_none()
            if doc:
                doc.status = status
                await db_session.commit()
            if progress_callback:
                await progress_callback(progress, step)
            logger.info(f"[{document_id}] {step} ({progress}%)")

        try:
            await update_status(DocumentStatus.PROCESSING, "Downloading file", 5)

            # 1. Get file bytes from MinIO
            file_bytes = await self._download_from_minio(storage_key)

            await update_status(DocumentStatus.PROCESSING, "Converting pages", 15)

            # 2. Convert PDF to images
            images = await asyncio.to_thread(self._pdf_to_images, file_bytes)
            page_count = len(images)
            logger.info(f"[{document_id}] {page_count} pages")

            await update_status(DocumentStatus.PROCESSING, "Running OCR (NPU)", 25)

            # 3. OCR each page
            ocr_start = time.perf_counter()
            all_text_parts = []
            ocr_meta_pages = []

            for i, image in enumerate(images):
                page_result = await asyncio.to_thread(
                    self._get_ocr().run, image
                )
                all_text_parts.append(f"[Page {i+1}]\n{page_result.full_text}")
                ocr_meta_pages.append({
                    "page": i + 1,
                    "line_count": page_result.line_count,
                    "char_count": len(page_result.full_text),
                })
                progress = 25 + int((i + 1) / page_count * 30)
                await update_status(
                    DocumentStatus.PROCESSING,
                    f"OCR page {i+1}/{page_count}",
                    progress,
                )

            full_text = "\n\n".join(all_text_parts)
            ocr_latency_ms = (time.perf_counter() - ocr_start) * 1000

            await update_status(DocumentStatus.PROCESSING, "Indexing for search", 60)

            # 4. Chunk the text
            chunks = self._chunk_text(full_text, chunk_size=512, overlap=64)
            logger.info(f"[{document_id}] {len(chunks)} chunks to embed")

            # 5. Embed chunks (NPU-accelerated)
            embed_start = time.perf_counter()
            texts = [c["text"] for c in chunks]
            embeddings = await asyncio.to_thread(
                self._get_embedder().embed, texts, 32
            )
            embed_latency_ms = (time.perf_counter() - embed_start) * 1000

            await update_status(DocumentStatus.PROCESSING, "Storing in vector DB", 80)

            # 6. Store in ChromaDB
            collection = self._get_chroma()
            collection.upsert(
                ids=[f"{document_id}_{i}" for i in range(len(chunks))],
                embeddings=embeddings.tolist(),
                documents=texts,
                metadatas=[
                    {
                        "document_id": str(document_id),
                        "chunk_index": c["index"],
                        "page_number": c["page_number"],
                        "char_start": c["char_start"],
                    }
                    for c in chunks
                ],
            )

            # 7. Save results to Postgres
            ocr_metadata = {
                "page_count": page_count,
                "chunk_count": len(chunks),
                "char_count": len(full_text),
                "ocr_latency_ms": round(ocr_latency_ms, 1),
                "embed_latency_ms": round(embed_latency_ms, 1),
                "ocr_provider": "PaddleOCR",
                "embed_provider": self._get_embedder().provider,
                "pages": ocr_meta_pages,
            }

            result = await db_session.execute(
                select(Document).where(Document.id == document_id)
            )
            doc = result.scalar_one_or_none()
            if doc:
                doc.status = DocumentStatus.DONE
                doc.extracted_text = full_text
                doc.ocr_metadata = ocr_metadata
                doc.page_count = page_count
                doc.processed_at = datetime.utcnow()
                await db_session.commit()

            await update_status(DocumentStatus.DONE, "Complete", 100)
            logger.success(
                f"[{document_id}] Done — OCR {ocr_latency_ms:.0f}ms, "
                f"Embed {embed_latency_ms:.0f}ms"
            )
            return ocr_metadata

        except Exception as e:
            logger.error(f"[{document_id}] Processing failed: {e}")
            from app.models.db_models import Document, DocumentStatus
            from sqlalchemy import select
            result = await db_session.execute(
                select(Document).where(Document.id == document_id)
            )
            doc = result.scalar_one_or_none()
            if doc:
                doc.status = DocumentStatus.FAILED
                doc.error_message = str(e)
                await db_session.commit()
            raise

    # ── Helpers ───────────────────────────────────────────────────────────────

    async def _download_from_minio(self, storage_key: str) -> bytes:
        from app.core.config import get_settings
        from minio import Minio
        settings = get_settings()
        client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_root_user,
            secret_key=settings.minio_root_password,
            secure=False,
        )
        response = client.get_object(settings.minio_bucket, storage_key)
        data = response.read()
        response.close()
        return data

    def _pdf_to_images(self, pdf_bytes: bytes):
        """Convert PDF bytes to list of PIL Images, one per page."""
        import fitz  # PyMuPDF
        from PIL import Image
        import io

        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        images = []
        for page in doc:
            # 2x resolution for better OCR accuracy
            mat = fitz.Matrix(2.0, 2.0)
            pix = page.get_pixmap(matrix=mat)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            images.append(img)
        doc.close()
        return images

    def _chunk_text(
        self,
        text: str,
        chunk_size: int = 512,
        overlap: int = 64,
    ) -> list[dict]:
        """
        Split text into overlapping chunks for RAG indexing.
        Overlap ensures context isn't lost at chunk boundaries.
        
        Each chunk dict: {text, index, char_start, page_number}
        """
        words = text.split()
        chunks = []
        i = 0
        chunk_index = 0

        while i < len(words):
            chunk_words = words[i : i + chunk_size]
            chunk_text = " ".join(chunk_words)

            # Determine which page this chunk is from
            char_start = len(" ".join(words[:i]))
            page_number = 1
            for line in text[:char_start].split("\n"):
                if line.startswith("[Page "):
                    try:
                        page_number = int(line.split("[Page ")[1].split("]")[0])
                    except (IndexError, ValueError):
                        pass

            chunks.append({
                "text": chunk_text,
                "index": chunk_index,
                "char_start": char_start,
                "page_number": page_number,
            })

            i += chunk_size - overlap
            chunk_index += 1

        return chunks


# Module-level singleton
_service: Optional[DocumentService] = None


def get_document_service() -> DocumentService:
    global _service
    if _service is None:
        _service = DocumentService()
    return _service
