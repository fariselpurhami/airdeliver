# file: apps/drone-control/main.py

from fastapi import FastAPI, WebSocket, Depends, HTTPException, status, WebSocketDisconnect
from typing import Dict
import json

from schemas.drone_commands import GoToPayload, DroneStatus
from services.task_queue import task_queue

app = FastAPI(title="Airdeliver Drone Control API")

async def get_validated_api_key(api_key: str | None = None):
    if not api_key or api_key != "secure-api-key-for-backend":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API Key")
    return api_key

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, drone_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[drone_id] = websocket

    def disconnect(self, drone_id: str):
        if drone_id in self.active_connections:
            del self.active_connections[drone_id]

    async def send_command(self, drone_id: str, command: dict):
        if drone_id in self.active_connections:
            await self.active_connections[drone_id].send_text(json.dumps(command))

manager = ConnectionManager()

@app.post("/drones/{drone_id}/takeoff")
async def command_takeoff(drone_id: str, secure_key: str = Depends(get_validated_api_key)):
    task = {"command": "takeoff", "payload": {"altitude": 15.0}}
    task_queue.add_task(drone_id, task)
    return {"message": f"Takeoff command queued for drone {drone_id}"}

@app.post("/drones/{drone_id}/goto")
async def command_goto(drone_id: str, payload: GoToPayload, secure_key: str = Depends(get_validated_api_key)):
    task = {"command": "goto", "payload": payload.dict()}
    task_queue.add_task(drone_id, task)
    return {"message": f"GoTo command queued for drone {drone_id}"}

@app.post("/drones/{drone_id}/land")
async def command_land(drone_id: str, secure_key: str = Depends(get_validated_api_key)):
    task = {"command": "land", "payload": {}}
    task_queue.add_task(drone_id, task)
    return {"message": f"Land command queued for drone {drone_id}"}

@app.websocket("/ws/drones/{drone_id}")
async def websocket_endpoint(websocket: WebSocket, drone_id: str):
    await manager.connect(drone_id, websocket)
    print(f"Drone {drone_id} connected.")
    try:
        while True:
            status_data = await websocket.receive_text()
            status = DroneStatus.parse_raw(status_data)
            print(f"Received status from {drone_id}: {status.status} at {status.battery_percent}% battery")

            next_task = task_queue.get_next_task(drone_id)
            if next_task:
                await manager.send_command(drone_id, next_task)
                print(f"Sent command {next_task['command']} to drone {drone_id}")

    except WebSocketDisconnect:
        manager.disconnect(drone_id)
        print(f"Drone {drone_id} disconnected.")
