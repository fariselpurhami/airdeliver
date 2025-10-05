# file: apps/drone-control/locustfile.py
# version: 1.0.0
# date: 2025-09-23
# author: Gemini

from locust import task, User
from locust_plugins.users.socketio import SocketIOUser
import random

class DroneUser(SocketIOUser):
    def on_start(self):
        self.drone_id = f"LOADTEST-{self.environment.runner.user_count}"
        self.host = "ws://localhost:8001"
        self.connect(f"/ws/drones/{self.drone_id}")

    @task
    def send_status(self):
        payload = {
            "drone_id": self.drone_id, "latitude": 34.0, "longitude": -118.0,
            "altitude": 50, "battery_percent": random.randint(20, 100), "status": "IN_TRANSIT"
        }
        self.send(payload)
