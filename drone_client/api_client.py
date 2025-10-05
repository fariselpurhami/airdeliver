# file: drone_client/api_client.py
# version: 1.0.0
# date: 2025-09-23
# author: Gemini

import asyncio
import websockets
import json
from drone_controller import DroneController

class ApiClient:
    def __init__(self, drone_id: str, uri: str, controller: DroneController):
        self.drone_id = drone_id
        self.uri = uri
        self.controller = controller
        self.command_queue = asyncio.Queue()

    async def _listen_for_commands(self, websocket):
        try:
            async for message in websocket:
                command = json.loads(message)
                print(f"Received command from server: {command}")
                await self.command_queue.put(command)
        except websockets.exceptions.ConnectionClosed:
            print("Connection with server closed.")

    async def _send_status_updates(self, websocket):
        while True:
            status_payload = self.controller.get_status_payload(self.drone_id)
            await websocket.send(json.dumps(status_payload))
            await asyncio.sleep(2) # Send status every 2 seconds

    async def _process_commands(self):
        while True:
            command = await self.command_queue.get()
            self.controller.execute_command(command)
            # Mark the task as done after execution
            self.command_queue.task_done()

    async def run(self):
        while True:
            try:
                async with websockets.connect(self.uri) as websocket:
                    print("Connected to Drone Control Server.")
                    # Run tasks concurrently
                    listen_task = asyncio.create_task(self._listen_for_commands(websocket))
                    status_task = asyncio.create_task(self._send_status_updates(websocket))
                    process_task = asyncio.create_task(self._process_commands())
                    await asyncio.gather(listen_task, status_task, process_task)
            except (websockets.exceptions.ConnectionClosedError, ConnectionRefusedError) as e:
                print(f"Connection failed: {e}. Retrying in 5 seconds...")
                await asyncio.sleep(5)
