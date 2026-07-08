from datetime import datetime
from typing import Literal
from typing import Optional

from pydantic import BaseModel, Field


class AttendanceRequest(BaseModel):
    employee_id: Optional[str] = Field(default=None, max_length=64)
    device_code: Optional[str] = Field(default=None, max_length=64)
    image_base64: str = Field(min_length=32)
    captured_at: Optional[datetime] = None


class AttendanceEventResponse(BaseModel):
    attempt_id: int
    action: Literal["checkin", "checkout"]
    matched: bool
    employee_id: Optional[str] = None
    similarity: float
    quality_score: float
    status: str


class AttendanceHistoryQuery(BaseModel):
    employee_id: Optional[str] = Field(default=None, max_length=64)
    limit: int = Field(default=20, ge=1, le=100)
