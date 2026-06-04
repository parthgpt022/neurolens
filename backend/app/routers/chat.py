"""
backend/app/routers/chat.py

Chat/RAG endpoints:
  POST /api/chat/sessions          — create a new chat session over document(s)
  GET  /api/chat/sessions          — list user's chat sessions
  GET  /api/chat/sessions/{id}     — session with full message history
  POST /api/chat/sessions/{id}/messages — send a message, get RAG answer
  DELETE /api/chat/sessions/{id}   — delete session + history
"""

import uuid
import time
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.db_models import User, Document, DocumentStatus, ChatSession, ChatMessage
from app.models.schemas import (
    ChatSessionCreate, ChatSessionResponse,
    ChatMessageResponse, ChatRequest, ChatResponse,
)
from app.services.auth_service import get_current_user
from app.services.rag_service import get_rag_service

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/sessions", response_model=ChatSessionResponse, status_code=201)
async def create_session(
    data: ChatSessionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verify all documents exist and belong to user and are processed
    for doc_id in data.document_ids:
        result = await db.execute(
            select(Document).where(
                Document.id == doc_id,
                Document.user_id == current_user.id,
            )
        )
        doc = result.scalar_one_or_none()
        if not doc:
            raise HTTPException(status_code=404, detail=f"Document {doc_id} not found")
        if doc.status != DocumentStatus.DONE:
            raise HTTPException(
                status_code=400,
                detail=f"Document {doc_id} is not fully processed yet (status: {doc.status})",
            )

    session = ChatSession(
        user_id=current_user.id,
        title=data.title or "New Chat",
        document_ids=[str(d) for d in data.document_ids],
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return ChatSessionResponse.model_validate(session)


@router.get("/sessions", response_model=list[ChatSessionResponse])
async def list_sessions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.user_id == current_user.id)
        .order_by(ChatSession.created_at.desc())
    )
    sessions = result.scalars().all()
    return [ChatSessionResponse.model_validate(s) for s in sessions]


@router.get("/sessions/{session_id}", response_model=dict)
async def get_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = await _get_owned_session(session_id, current_user.id, db)
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at)
    )
    messages = result.scalars().all()

    return {
        **ChatSessionResponse.model_validate(session).model_dump(),
        "messages": [ChatMessageResponse.model_validate(m).model_dump() for m in messages],
    }


@router.post("/sessions/{session_id}/messages", response_model=ChatResponse)
async def send_message(
    session_id: uuid.UUID,
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    The core RAG endpoint.
    1. Save the user message
    2. Retrieve chat history for context
    3. Call RAG service → answer + citations
    4. Save assistant message
    5. Return response
    """
    session = await _get_owned_session(session_id, current_user.id, db)

    # Save user message
    user_msg = ChatMessage(
        session_id=session_id,
        role="user",
        content=request.message,
    )
    db.add(user_msg)
    await db.commit()

    # Get recent chat history for multi-turn context
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(12)  # Last 6 turns
    )
    history_rows = result.scalars().all()
    chat_history = [
        {"role": m.role, "content": m.content}
        for m in reversed(history_rows)
        if m.id != user_msg.id  # Exclude the message we just added
    ]

    # Call RAG
    doc_ids = [uuid.UUID(d) for d in session.document_ids]
    rag_result = await get_rag_service().answer(
        query=request.message,
        document_ids=doc_ids,
        chat_history=chat_history,
    )

    # Save assistant message
    assistant_msg = ChatMessage(
        session_id=session_id,
        role="assistant",
        content=rag_result["answer"],
        citations=rag_result["citations"],
        latency_ms=rag_result["latency_ms"],
    )
    db.add(assistant_msg)
    await db.commit()
    await db.refresh(assistant_msg)

    return ChatResponse(
        answer=rag_result["answer"],
        citations=rag_result["citations"],
        latency_ms=rag_result["latency_ms"],
        message_id=assistant_msg.id,
    )


@router.delete("/sessions/{session_id}", status_code=204)
async def delete_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = await _get_owned_session(session_id, current_user.id, db)
    await db.delete(session)
    await db.commit()


async def _get_owned_session(
    session_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession
) -> ChatSession:
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.user_id == user_id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return session
