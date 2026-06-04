"""
backend/app/models/schemas.py

Pydantic v2 schemas for API request/response validation.
These are separate from the ORM models intentionally — the API shape
and the DB shape are allowed to differ.
"""

import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


# ─── Auth ─────────────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=8)


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    name: str
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# ─── Document ─────────────────────────────────────────────────────────────────

class DocumentResponse(BaseModel):
    id: uuid.UUID
    filename: str
    original_filename: str
    page_count: int
    status: str
    file_size_bytes: int
    created_at: datetime
    processed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class DocumentDetailResponse(DocumentResponse):
    extracted_text: Optional[str] = None
    ocr_metadata: Optional[dict] = None


class EntityResponse(BaseModel):
    id: uuid.UUID
    entity_type: str
    value: str
    normalized_value: Optional[str] = None
    confidence: float
    page_number: int
    bbox: Optional[dict] = None

    model_config = {"from_attributes": True}


# ─── Chat ─────────────────────────────────────────────────────────────────────

class ChatSessionCreate(BaseModel):
    document_ids: list[uuid.UUID]
    title: Optional[str] = "New Chat"


class ChatSessionResponse(BaseModel):
    id: uuid.UUID
    title: str
    document_ids: list
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatMessageResponse(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    citations: Optional[list] = None
    latency_ms: Optional[float] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    session_id: uuid.UUID


class ChatResponse(BaseModel):
    answer: str
    citations: list[dict]
    latency_ms: float
    message_id: uuid.UUID


# ─── Processing ───────────────────────────────────────────────────────────────

class ProcessingStatusResponse(BaseModel):
    document_id: uuid.UUID
    status: str
    progress_percent: int
    current_step: str
    error: Optional[str] = None
