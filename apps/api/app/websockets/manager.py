# file: apps/api/app/websockets/manager.py
# version: 1.0.0
# date: 2025-09-23
# author: Gemini 2.5 Pro

from fastapi import WebSocket
from typing import Dict, List

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, List[WebSocket]] = {} # order_id -> [websockets]

    async def connect(self, websocket: WebSocket, order_id: int):
        await websocket.accept()
        if order_id not in self.active_connections:
            self.active_connections[order_id] = []
        self.active_connections[order_id].append(websocket)

    def disconnect(self, websocket: WebSocket, order_id: int):
        if order_id in self.active_connections:
            self.active_connections[order_id].remove(websocket)
            if not self.active_connections[order_id]:
                del self.active_connections[order_id]

    async def broadcast_to_order(self, order_id: int, message: str):
        if order_id in self.active_connections:
            for connection in self.active_connections[order_id]:
                await connection.send_text(message)

manager = ConnectionManager()
