# drone-simulator/virtual_drone.py

import asyncio
import json
import websockets
import random

class VirtualDrone:
    def __init__(self, drone_id):
        self.id = drone_id
        self.lat, self.lon, self.alt = 34.0522, -118.2437, 0
        self.battery = 100.0
        self.status = "IDLE"

    async def simulate_flight_to(self, lat, lon, alt):
        print(f"[{self.id}] Flying to {lat}, {lon}...")
        self.status = "IN_TRANSIT"
        await asyncio.sleep(random.uniform(5, 10))
        self.lat, self.lon, self.alt = lat, lon, alt
        self.battery -= random.uniform(5, 10)
        self.status = "IDLE"
        print(f"[{self.id}] Arrived. Battery at {self.battery:.1f}%")

    async def connect_and_run(self):
        uri = f"ws://localhost:8001/ws/drones/{self.id}"
        while self.battery > 15: 
            try:
                async with websockets.connect(uri) as websocket:
                    print(f"[{self.id}] Connected to Drone Control Server.")
                    while self.battery > 15
                        status_payload = json.dumps({
                            "drone_id": self.id, "latitude": self.lat, "longitude": self.lon,
                            "altitude": self.alt, "battery_percent": int(self.battery), "status": self.status
                        })
                        await websocket.send(status_payload)
                        s
                        try:
                            cmd_str = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                            cmd = json.loads(cmd_str)
                            if cmd['command'] == 'goto':
                                await self.simulate_flight_to(**cmd['payload'])
                        except asyncio.TimeoutError:
                            pass 
                        
                        self.battery -= 0.1 
                        await asyncio.sleep(2)
            except (websockets.exceptions.ConnectionClosed, ConnectionRefusedError) as e:
                print(f"[{self.id}] Connection failed: {e}. Retrying in 5 seconds...")
                await asyncio.sleep(5)
        
        print(f"[{self.id}] Low battery, simulation ended.")

async def main():
    drones = [VirtualDrone(f"SIM-{i:03d}") for i in range(5)]
    await asyncio.gather(*(d.connect_and_run() for d in drones))

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Simulation stopped by user.")
