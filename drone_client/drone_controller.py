# file: drone_client/drone_controller.py

import time

class MockDroneSDK:
    def __init__(self):
        self.is_armed = False
        self.location = (34.0522, -118.2437, 0)
        self.battery = 100

    def connect(self, connection_string):
        print(f"Connecting to vehicle on: {connection_string}")
        time.sleep(1)
        print("Vehicle connected.")

    def arm(self):
        print("Arming motors...")
        time.sleep(1)
        self.is_armed = True
        print("Motors armed.")

    def takeoff(self, altitude):
        print(f"Taking off to {altitude} meters.")
        self.location = (self.location[0], self.location[1], altitude)
        time.sleep(3)
        print("Takeoff complete.")

    def goto(self, lat, lon, alt):
        print(f"Flying to location: LAT={lat}, LON={lon}, ALT={alt}")
        self.location = (lat, lon, alt)
        # Simulate flight time
        time.sleep(5)
        print("Arrived at destination.")

    def land(self):
        print("Landing...")
        self.location = (self.location[0], self.location[1], 0)
        self.is_armed = False
        time.sleep(2)
        print("Landed and disarmed.")

    def get_battery(self):
        self.battery -= 0.1
        return max(0, int(self.battery))

    def get_location(self):
        return self.location

class DroneController:
    def __init__(self):
        self.vehicle = MockDroneSDK()
        self.status = "IDLE"
        self.vehicle.connect("udp:127.0.0.1:14550") 

    def execute_command(self, command: dict):
        cmd_type = command.get("command")
        payload = command.get("payload", {})
        print(f"Executing command: {cmd_type}")

        if cmd_type == "takeoff":
            self.status = "TAKING_OFF"
            if not self.vehicle.is_armed:
                self.vehicle.arm()
            self.vehicle.takeoff(payload.get("altitude", 10))
            self.status = "IDLE"

        elif cmd_type == "goto":
            self.status = "IN_TRANSIT"
            self.vehicle.goto(payload["latitude"], payload["longitude"], payload["altitude"])
            self.status = "IDLE" 

        elif cmd_type == "land":
            self.status = "LANDING"
            self.vehicle.land()
            self.status = "IDLE"

        else:
            print(f"Unknown command: {cmd_type}")

    def get_status_payload(self, drone_id: str) -> dict:
        loc = self.vehicle.get_location()
        return {
            "drone_id": drone_id,
            "latitude": loc[0],
            "longitude": loc[1],
            "altitude": loc[2],
            "battery_percent": self.vehicle.get_battery(),
            "status": self.status
        }
