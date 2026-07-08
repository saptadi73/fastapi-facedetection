from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CameraMeta:
    device_code: str | None
    width: int
    height: int


class CameraService:
    def parse_meta(self, device_code: str | None, width: int, height: int) -> CameraMeta:
        return CameraMeta(device_code=device_code, width=width, height=height)


camera_service = CameraService()
