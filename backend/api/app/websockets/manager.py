# backend/api/app/websockets/manager.py

from fastapi import WebSocket
from typing import Dict, List

class ConnectionManager:

    def __init__(self):
        self.active_connections: Dict[int, List[WebSocket]] = {} 

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
