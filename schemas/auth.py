from typing import Optional

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=255)
    odoo_base_url: Optional[str] = Field(default=None, min_length=1, max_length=512)
    odoo_db: Optional[str] = Field(default=None, min_length=1, max_length=128)


class LoginResponseData(BaseModel):
    uid: int
    username: str
    name: Optional[str] = None
    session_id: Optional[str] = None
    odoo_base_url: Optional[str] = None
    odoo_db: Optional[str] = None
    user_context: dict
    employee: Optional[dict] = None
    employee_map_id: Optional[int] = None
    employee_resolved: bool = False
    employee_error: Optional[str] = None
