from datetime import datetime
from typing import Literal
from typing import Optional

from pydantic import BaseModel, Field


class AttendanceRequest(BaseModel):
    employee_id: Optional[str] = Field(default=None, max_length=64)
    device_code: Optional[str] = Field(default=None, max_length=64)
    image_base64: str = Field(min_length=32)
    captured_at: Optional[datetime] = None
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    gps_accuracy_meters: Optional[float] = Field(default=None, ge=0)
    gps_provider: Optional[str] = Field(default=None, max_length=32)


class AttendanceEventResponse(BaseModel):
    attempt_id: int
    action: Literal["checkin", "checkout"]
    matched: bool
    employee_id: Optional[str] = None
    similarity: float
    quality_score: float
    status: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    gps_accuracy_meters: Optional[float] = None


class AttendanceHistoryQuery(BaseModel):
    employee_id: Optional[str] = Field(default=None, max_length=64)
    limit: int = Field(default=20, ge=1, le=100)
