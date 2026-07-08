from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class APIEnvelope(BaseModel):
    success: bool
    code: str
    message: str
    data: Optional[Any] = None
    errors: Optional[Any] = None
    meta: Optional[dict[str, Any]] = None
    timestamp_utc: datetime


class PagingQuery(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class PaginationMeta(BaseModel):
    page: int
    page_size: int
    total_pages: int


class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
