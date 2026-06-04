"""
backend/app/routers/websocket.py

WebSocket endpoint for real-time document processing status.
The frontend connects here right after uploading a document and receives
live progress updates: "OCR page 2/5", "Indexing...", "Complete!"

This is a great demo feature — you can see the progress bar move in real time.
"""

import uuid
import asyncio
import json
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from loguru import logger

router = APIRouter(tags=["websocket"])


class ConnectionManager:
    """Manages active WebSocket connections, keyed by document_id."""

    def __init__(self):
        # document_id (str) → WebSocket
        self._connections: dict[str, WebSocket] = {}

    async def connect(self, document_id: str, websocket: WebSocket):
        await websocket.accept()
        self._connections[document_id] = websocket
        logger.info(f"WS connected for document {document_id}")

    def disconnect(self, document_id: str):
        self._connections.pop(document_id, None)
        logger.info(f"WS disconnected for document {document_id}")

    async def send_progress(
        self,
        document_id: str,
        progress: int,
        step: str,
        status: str = "processing",
        error: Optional[str] = None,
    ):
        ws = self._connections.get(document_id)
        if ws:
            try:
                await ws.send_json({
                    "document_id": document_id,
                    "progress": progress,
                    "step": step,
                    "status": status,
                    "error": error,
                })
            except Exception as e:
                logger.warning(f"WS send failed for {document_id}: {e}")
                self.disconnect(document_id)


# Global singleton — imported by document_service to push updates
manager = ConnectionManager()


@router.websocket("/ws/processing/{document_id}")
async def processing_status(websocket: WebSocket, document_id: str):
    """
    Connect to receive real-time processing updates for a document.
    
    Frontend usage:
        const ws = new WebSocket(`ws://localhost:8000/ws/processing/${docId}`);
        ws.onmessage = (e) => {
            const { progress, step, status } = JSON.parse(e.data);
            updateProgressBar(progress, step);
        };
    """
    await manager.connect(document_id, websocket)
    try:
        # Keep connection alive — wait for client to disconnect
        while True:
            # Heartbeat every 5s so connection doesn't time out
            await asyncio.sleep(5)
            try:
                await websocket.send_json({"type": "heartbeat"})
            except Exception:
                break
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(document_id)
