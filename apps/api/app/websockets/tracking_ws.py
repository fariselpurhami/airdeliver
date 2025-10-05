# file: apps/api/app/websockets/tracking_ws.py
# version: 1.0.0
# date: 2025-09-30
# author: Gemini

import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from typing import List, Dict

from app.api import deps
from app.models.user import User

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        # Maps order_id to a list of active connections for that order
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, order_id: str):
        await websocket.accept()
        if order_id not in self.active_connections:
            self.active_connections[order_id] = []
        self.active_connections[order_id].append(websocket)

    def disconnect(self, websocket: WebSocket, order_id: str):
        self.active_connections[order_id].remove(websocket)
        if not self.active_connections[order_id]:
            del self.active_connections[order_id]

    async def broadcast_to_order(self, order_id: str, message: str):
        if order_id in self.active_connections:
            for connection in self.active_connections[order_id]:
                await connection.send_text(message)

manager = ConnectionManager()

async def drone_position_simulator(order_id: str):
    """
    Simulates a drone's movement and broadcasts its position.
    """
    # Initial position (e.g., warehouse)
    lat, lon = 34.0522, -118.2437
    
    while True:
        # Simulate movement
        lat += 0.0005
        lon += 0.0005
        
        position_data = {
            "order_id": order_id,
            "lat": lat,
            "lon": lon,
            "status": "IN_TRANSIT"
        }
        await manager.broadcast_to_order(order_id, json.dumps(position_data))
        await asyncio.sleep(2) # Send update every 2 seconds

@router.websocket("/track/{order_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    order_id: str,
    # Optional: Secure the endpoint by requiring a valid user token
    # current_user: User = Depends(deps.get_current_active_user)
):
    """
    WebSocket endpoint for live order tracking.
    """
    await manager.connect(websocket, order_id)
    # Start the drone simulator for this specific order
    simulator_task = asyncio.create_task(drone_position_simulator(order_id))
    try:
        while True:
            # Keep the connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, order_id)
        simulator_task.cancel() # Stop the simulator when the user disconnects
        print(f"Client disconnected from order {order_id}. Simulator stopped.")
