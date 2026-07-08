from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class EnrollmentStartRequest(BaseModel):
    employee_id: str = Field(min_length=1, max_length=64)
    employee_name: str = Field(min_length=1, max_length=255)
    employee_code: Optional[str] = Field(default=None, max_length=64)


class EnrollmentSampleRequest(BaseModel):
    employee_id: str = Field(min_length=1, max_length=64)
    image_base64: str = Field(min_length=32)


class EnrollmentFinishRequest(BaseModel):
    employee_id: str = Field(min_length=1, max_length=64)
    notes: Optional[str] = Field(default=None, max_length=1000)


class EnrollmentStatusResponse(BaseModel):
    employee_id: str
    employee_name: str
    status: str
    total_samples: int
    accepted_samples: int
    is_enrolled: bool
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
