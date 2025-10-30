# apps/api/app/services/compliance_service.py

from typing import List, Tuple
import math

NO_FLY_ZONES = [
    {"name": "Major Airport", "lat": 33.9416, "lon": -118.4085, "radius_km": 5.0},
    {"name": "Government Building", "lat": 34.0549, "lon": -118.2426, "radius_km": 1.5},
]

class ComplianceService:
    def _haversine_distance(self, lat1, lon1, lat2, lon2) -> float:
        R = 6371
        dLat = math.radians(lat2 - lat1)
        dLon = math.radians(lon2 - lon1)
        a = math.sin(dLat / 2) * math.sin(dLat / 2) + math.cos(math.radians(lat1)) \
            * math.cos(math.radians(lat2)) * math.sin(dLon / 2) * math.sin(dLon / 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    def validate_flight_path(self, start_coords: Tuple[float, float], end_coords: Tuple[float, float]) -> bool:
        
        for zone in NO_FLY_ZONES:
            dist_to_end = self._haversine_distance(end_coords[0], end_coords[1], zone["lat"], zone["lon"])
            if dist_to_end <= zone["radius_km"]:
                print(f"VIOLATION: Delivery destination is inside No-Fly Zone '{zone['name']}'")
                return False
        return True

compliance_service = ComplianceService()
