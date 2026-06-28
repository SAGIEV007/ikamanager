"""WebSocket for real-time updates."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List
import json
import asyncio

router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        """Send a message to all connected clients."""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)

        for conn in disconnected:
            self.active_connections.remove(conn)

    async def send_to_client(self, websocket: WebSocket, message: dict):
        """Send a message to a specific client."""
        try:
            await websocket.send_json(message)
        except Exception:
            pass


manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time status updates."""
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle incoming messages (e.g., subscribe to specific accounts)
            try:
                message = json.loads(data)
                if message.get("type") == "ping":
                    await manager.send_to_client(websocket, {"type": "pong"})
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        manager.disconnect(websocket)


async def broadcast_account_status(account_id: int, status: str, message: str = ""):
    """Broadcast account status change to all clients."""
    await manager.broadcast({
        "type": "account_status",
        "account_id": account_id,
        "status": status,
        "message": message,
    })


async def broadcast_task_update(task_id: int, account_id: int, status: str, details: dict = None):
    """Broadcast task update to all clients."""
    await manager.broadcast({
        "type": "task_update",
        "task_id": task_id,
        "account_id": account_id,
        "status": status,
        "details": details or {},
    })


async def broadcast_log(account_id: int, action: str, message: str, level: str = "info"):
    """Broadcast a log entry."""
    await manager.broadcast({
        "type": "log",
        "account_id": account_id,
        "action": action,
        "message": message,
        "level": level,
    })
