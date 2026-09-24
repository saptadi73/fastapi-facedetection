from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from schemas.hr import OvertimeCreateRequest, TimeOffCreateRequest
from services.odoo_service import odoo_service
from supports import error_response, success_response
from supports.security import enforce_employee_scope, require_api_key


router = APIRouter(
    prefix="/api/v1/hr",
    tags=["HR"],
    dependencies=[Depends(require_api_key)],
)


def _odoo_error(exc: Exception):
    return error_response(message="Odoo HR request failed", status_code=502, code="ODOO_HR_ERROR", errors={"detail": str(exc)})


def _ensure_owned_record(record_id: int, records: list[dict], auth: dict) -> None:
    """Require a self-service token to access a record it owns."""
    if not auth.get("employee_id") or not any(str(item.get("id")) == str(record_id) for item in records):
        raise HTTPException(status_code=403, detail="The authenticated user does not own this record")


@router.get("/timeoff/types")
def timeoff_types():
    try:
        return success_response(message="Time off types fetched", code="TIMEOFF_TYPES", data={"items": odoo_service.list_timeoff_types()})
    except Exception as exc:
        return _odoo_error(exc)


@router.get("/timeoff")
def list_timeoff(employee_id: str = Query(min_length=1, max_length=64), auth: dict = Depends(require_api_key)):
    enforce_employee_scope(employee_id, auth)
    try:
        items = odoo_service.list_timeoffs(employee_id)
        return success_response(message="Time off requests fetched", code="TIMEOFF_LIST", data={"items": items, "total": len(items)})
    except Exception as exc:
        return _odoo_error(exc)


@router.post("/timeoff", status_code=201)
def create_timeoff(payload: TimeOffCreateRequest, auth: dict = Depends(require_api_key)):
    enforce_employee_scope(payload.employee_id, auth)
    if payload.date_to < payload.date_from:
        return error_response(message="date_to must be on or after date_from", status_code=422, code="INVALID_DATE_RANGE")
    try:
        result = odoo_service.create_timeoff(
            payload.employee_id, payload.leave_type_id, payload.date_from.isoformat(), payload.date_to.isoformat(), payload.description,
        )
        return success_response(message="Time off request created", status_code=201, code="TIMEOFF_CREATED", data=result)
    except Exception as exc:
        return _odoo_error(exc)


@router.post("/timeoff/{leave_id}/cancel")
def cancel_timeoff(leave_id: int, auth: dict = Depends(require_api_key)):
    try:
        if auth.get("auth_type") not in {"api_key", "disabled"}:
            _ensure_owned_record(leave_id, odoo_service.list_timeoffs(str(auth["employee_id"])), auth)
        odoo_service.cancel_timeoff(leave_id)
        return success_response(message="Time off request cancelled", code="TIMEOFF_CANCELLED", data={"id": leave_id})
    except HTTPException:
        raise
    except Exception as exc:
        return _odoo_error(exc)


@router.get("/overtime")
def list_overtime(employee_id: str = Query(min_length=1, max_length=64), auth: dict = Depends(require_api_key)):
    enforce_employee_scope(employee_id, auth)
    try:
        items = odoo_service.list_overtimes(employee_id)
        return success_response(message="Overtime requests fetched", code="OVERTIME_LIST", data={"items": items, "total": len(items)})
    except Exception as exc:
        return _odoo_error(exc)


@router.post("/overtime", status_code=201)
def create_overtime(payload: OvertimeCreateRequest, auth: dict = Depends(require_api_key)):
    enforce_employee_scope(payload.employee_id, auth)
    try:
        result = odoo_service.create_overtime(
            payload.employee_id, payload.date.isoformat(), payload.duration_hours, payload.description,
        )
        return success_response(message="Overtime request created", status_code=201, code="OVERTIME_CREATED", data=result)
    except Exception as exc:
        return _odoo_error(exc)


@router.get("/payroll/payslips")
def list_payslips(employee_id: str = Query(min_length=1, max_length=64), auth: dict = Depends(require_api_key)):
    enforce_employee_scope(employee_id, auth)
    try:
        items = odoo_service.list_payslips(employee_id)
        return success_response(message="Payslips fetched", code="PAYSLIP_LIST", data={"items": items, "total": len(items)})
    except Exception as exc:
        return _odoo_error(exc)


@router.get("/payroll/payslips/{payslip_id}/pdf")
def download_payslip(payslip_id: int, auth: dict = Depends(require_api_key)):
    try:
        if auth.get("auth_type") not in {"api_key", "disabled"}:
            _ensure_owned_record(payslip_id, odoo_service.list_payslips(str(auth["employee_id"])), auth)
        content, filename = odoo_service.payslip_pdf(payslip_id)
        return Response(content=content, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{filename}"'})
    except HTTPException:
        raise
    except Exception as exc:
        return _odoo_error(exc)
