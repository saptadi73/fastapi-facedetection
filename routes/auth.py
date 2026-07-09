from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from config.database import get_db
from models.face_attendance import FaceEmployeeMap
from schemas.auth import LoginRequest
from services.odoo_service import odoo_service
from supports import error_response, success_response

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])


@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    result = odoo_service.authenticate(
        username=payload.username,
        password=payload.password,
        odoo_base_url=payload.odoo_base_url,
        odoo_db=payload.odoo_db,
    )
    if not result.success:
        return error_response(
            message="Login failed",
            status_code=401,
            code="ODOO_LOGIN_FAILED",
            errors={"detail": result.error},
        )

    employee_map = None
    if result.employee:
        employee_map = _upsert_employee_map_from_odoo_login(
            db=db,
            employee=result.employee,
            odoo_user_id=result.uid,
            login_email=result.username or payload.username,
        )

    return success_response(
        message="Login successful",
        code="LOGIN_SUCCESS",
        data={
            "uid": result.uid,
            "username": result.username,
            "name": result.name,
            "session_id": result.session_id,
            "odoo_base_url": payload.odoo_base_url,
            "odoo_db": payload.odoo_db,
            "user_context": result.user_context,
            "employee": result.employee,
            "employee_map_id": employee_map.id if employee_map else None,
            "employee_resolved": employee_map is not None,
            "employee_error": result.employee_error,
        },
    )


def _upsert_employee_map_from_odoo_login(
    db: Session,
    employee: dict,
    odoo_user_id: Optional[int],
    login_email: str,
) -> FaceEmployeeMap:
    employee_id = str(employee["id"])
    employee_map = db.scalar(select(FaceEmployeeMap).where(FaceEmployeeMap.employee_id == employee_id))
    if employee_map is None:
        employee_map = FaceEmployeeMap(
            employee_id=employee_id,
            employee_code=employee.get("barcode") or employee.get("identification_id"),
            employee_name=employee.get("name") or login_email,
            odoo_user_id=odoo_user_id,
            login_email=login_email,
            is_active=True,
            is_enrolled=False,
        )
        db.add(employee_map)
    else:
        employee_map.employee_code = employee.get("barcode") or employee.get("identification_id")
        employee_map.employee_name = employee.get("name") or employee_map.employee_name
        employee_map.odoo_user_id = odoo_user_id
        employee_map.login_email = login_email
        employee_map.is_active = True

    db.commit()
    db.refresh(employee_map)
    return employee_map
