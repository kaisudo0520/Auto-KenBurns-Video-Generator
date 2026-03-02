"""
WebSocket Router

Handles real-time rendering progress updates via WebSocket connections.
"""

import asyncio
import json
import logging
from typing import Dict, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from backend import deps
from backend.models.render_job import RenderJob
from backend.models.render_job import JobStatus

logger = logging.getLogger(__name__)
router = APIRouter()


# Connection manager for WebSocket connections
class ConnectionManager:
    """Manages WebSocket connections for render progress updates."""

    def __init__(self):
        # job_id -> set of websockets
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, job_id: str):
        """Connect a WebSocket to receive updates for a specific job."""
        await websocket.accept()
        if job_id not in self.active_connections:
            self.active_connections[job_id] = set()
        self.active_connections[job_id].add(websocket)
        logger.info(f"WebSocket connected for job {job_id}. Total connections: {len(self.active_connections[job_id])}")

    def disconnect(self, websocket: WebSocket, job_id: str):
        """Disconnect a WebSocket from a job's updates."""
        if job_id in self.active_connections:
            self.active_connections[job_id].discard(websocket)
            if not self.active_connections[job_id]:
                del self.active_connections[job_id]
            logger.info(f"WebSocket disconnected for job {job_id}")

    async def send_message(self, job_id: str, message: dict):
        """Send a message to all connections for a specific job."""
        if job_id in self.active_connections:
            # 複製一份避免迭代時修改原始集合
            connections = list(self.active_connections[job_id])
            for connection in connections:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Failed to send message to connection: {e}")
                    # 從原始集合中移除失敗的連線
                    self.active_connections[job_id].discard(connection)

    async def broadcast_progress(self, job_id: str, progress_data: dict):
        """Broadcast progress update to all connections for a job."""
        message = {
            "type": "progress",
            "data": progress_data,
        }
        await self.send_message(job_id, message)

    async def broadcast_status(self, job_id: str, status_data: dict):
        """Broadcast status update to all connections for a job."""
        message = {
            "type": "status",
            "data": status_data,
        }
        await self.send_message(job_id, message)

    async def broadcast_complete(self, job_id: str, complete_data: dict):
        """Broadcast completion to all connections for a job."""
        message = {
            "type": "complete",
            "data": complete_data,
        }
        await self.send_message(job_id, message)

    async def broadcast_error(self, job_id: str, error_data: dict):
        """Broadcast error to all connections for a job."""
        message = {
            "type": "error",
            "data": error_data,
        }
        await self.send_message(job_id, message)


# Global connection manager
manager = ConnectionManager()


@router.websocket("/render/{job_id}")
async def websocket_render_progress(websocket: WebSocket, job_id: str):
    """
    WebSocket endpoint for real-time render progress updates.

    Connect to receive progress updates for a specific render job.

    Client can send:
    - {"type": "subscribe", "job_id": "xxx"} - Subscribe to job updates
    - {"type": "unsubscribe", "job_id": "xxx"} - Unsubscribe from job updates

    Server will send:
    - {"type": "connected", "data": {...}} - Connection confirmed
    - {"type": "progress", "data": {...}} - Progress update
    - {"type": "status", "data": {...}} - Status change
    - {"type": "complete", "data": {...}} - Render completed
    - {"type": "error", "data": {...}} - Error occurred
    """
    # Accept the connection
    await manager.connect(websocket, job_id)

    try:
        # Send connection confirmation
        await websocket.send_json({
            "type": "connected",
            "data": {
                "job_id": job_id,
                "message": "已連接到渲染進度服務"
            }
        })

        # Get initial job status
        db = next(deps.get_db())
        try:
            job = db.query(RenderJob).filter(RenderJob.id == job_id).first()
            if job:
                await websocket.send_json({
                    "type": "status",
                    "data": {
                        "job_id": job_id,
                        "status": job.status.value,
                        "message": f"任務狀態: {job.status.value}",
                    }
                })
        finally:
            db.close()

        # Handle incoming messages
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)

                if message.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})

            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON received from client")
            except Exception as e:
                logger.error(f"Error handling WebSocket message: {e}")

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for job {job_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        manager.disconnect(websocket, job_id)


# Helper function to broadcast progress from render service
async def broadcast_job_progress(job_id: str, **kwargs):
    """Broadcast progress update for a job."""
    await manager.broadcast_progress(job_id, {
        "job_id": job_id,
        **kwargs,
    })


async def broadcast_job_status(job_id: str, status: str, message: str = None):
    """Broadcast status update for a job."""
    await manager.broadcast_status(job_id, {
        "job_id": job_id,
        "status": status,
        "message": message or f"狀態變更為: {status}",
    })


async def broadcast_job_complete(job_id: str, output_path: str = None, **kwargs):
    """Broadcast completion for a job."""
    await manager.broadcast_complete(job_id, {
        "job_id": job_id,
        "status": "completed",
        "output_path": output_path,
        **kwargs,
    })


async def broadcast_job_error(job_id: str, error: str, code: str = None):
    """Broadcast error for a job."""
    await manager.broadcast_error(job_id, {
        "job_id": job_id,
        "error": error,
        "code": code,
    })
