from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class DeviceCreateRequest(BaseModel):
    device_code: str = Field(min_length=1, max_length=64)
    device_name: str = Field(min_length=1, max_length=128)
    location: Optional[str] = Field(default=None, max_length=255)


class DeviceResponse(BaseModel):
    id: int
    device_code: str
    device_name: str
    location: Optional[str] = None
    is_active: bool
    last_seen_at: Optional[datetime] = None
