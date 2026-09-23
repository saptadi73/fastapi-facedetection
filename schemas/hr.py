from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class TimeOffCreateRequest(BaseModel):
    employee_id: str = Field(min_length=1, max_length=64)
    leave_type_id: int = Field(gt=0)
    date_from: date
    date_to: date
    description: str = Field(min_length=1, max_length=1000)


class OvertimeCreateRequest(BaseModel):
    employee_id: str = Field(min_length=1, max_length=64)
    date: date
    duration_hours: float = Field(gt=0, le=24)
    description: str = Field(min_length=1, max_length=1000)
