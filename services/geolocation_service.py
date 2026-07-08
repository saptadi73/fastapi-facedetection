from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional


@dataclass
class GPSPayload:
    latitude: Optional[float]
    longitude: Optional[float]
    gps_accuracy_meters: Optional[float]
    gps_provider: Optional[str]


class GeolocationService:
    def normalize(
        self,
        latitude: Optional[float],
        longitude: Optional[float],
        gps_accuracy_meters: Optional[float],
        gps_provider: Optional[str],
    ) -> GPSPayload:
        if latitude is None or longitude is None:
            return GPSPayload(None, None, None, gps_provider)

        return GPSPayload(
            latitude=round(latitude, 7),
            longitude=round(longitude, 7),
            gps_accuracy_meters=round(gps_accuracy_meters, 2) if gps_accuracy_meters is not None else None,
            gps_provider=gps_provider,
        )

    def has_fix(self, payload: GPSPayload) -> bool:
        return payload.latitude is not None and payload.longitude is not None

    def distance_meters(
        self,
        latitude_a: float,
        longitude_a: float,
        latitude_b: float,
        longitude_b: float,
    ) -> float:
        radius_earth = 6371000.0
        lat1 = math.radians(latitude_a)
        lat2 = math.radians(latitude_b)
        delta_lat = math.radians(latitude_b - latitude_a)
        delta_lon = math.radians(longitude_b - longitude_a)

        hav = (
            math.sin(delta_lat / 2) ** 2
            + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon / 2) ** 2
        )
        arc = 2 * math.atan2(math.sqrt(hav), math.sqrt(1 - hav))
        return radius_earth * arc


geolocation_service = GeolocationService()
