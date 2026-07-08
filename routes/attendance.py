from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from config.database import get_db
from models.face_attendance import (
    FaceAttendanceAttempt,
    FaceDetectionResult,
    FaceDevice,
    FaceEmployeeMap,
    FaceRecognitionResult,
    OdooAttendanceSync,
)
from schemas.attendance import AttendanceRequest
from services.embedding_service import embedding_service
from services.faiss_service import faiss_service
from services.image_service import image_service
from services.mediapipe_service import mediapipe_service
from services.odoo_service import odoo_service
from supports import error_response, success_response

router = APIRouter(prefix="/api/v1/attendance", tags=["Attendance"])


def _resolve_device(db: Session, device_code: Optional[str]) -> Optional[FaceDevice]:
    if not device_code:
        return None
    return db.scalar(select(FaceDevice).where(FaceDevice.device_code == device_code))


def _run_attendance(action: str, payload: AttendanceRequest, db: Session):
    image_bytes = image_service.decode_base64(payload.image_base64)
    image = image_service.open_image(image_bytes)
    quality = image_service.evaluate_quality(image)
    face = mediapipe_service.detect(image.width, image.height)

    if face.face_count != 1:
        return error_response(
            message="Face validation failed: exactly 1 face required",
            status_code=422,
            code="INVALID_FACE_COUNT",
            data={"face_count": face.face_count},
        )

    device = _resolve_device(db, payload.device_code)
    attempt = FaceAttendanceAttempt(
        device_id=device.id if device else None,
        action=action,
        captured_at=payload.captured_at or datetime.now(timezone.utc),
        face_count=face.face_count,
        quality_score=(quality.blur_score + quality.brightness_score) / 2,
        status="pending",
    )
    db.add(attempt)
    db.flush()

    detection = FaceDetectionResult(
        attempt_id=attempt.id,
        confidence=face.confidence,
        yaw=face.yaw,
        pitch=face.pitch,
        roll=face.roll,
        is_valid=face.confidence >= 0.7,
    )
    db.add(detection)

    embedding = embedding_service.generate_embedding(image_bytes)
    match = faiss_service.search(embedding=embedding, threshold=0.75)

    recognition = FaceRecognitionResult(
        attempt_id=attempt.id,
        employee_map_id=match.employee_map_id,
        similarity=match.similarity,
        threshold=0.75,
        matched=match.employee_map_id is not None,
    )
    db.add(recognition)

    employee_id: Optional[str] = None
    if match.employee_map_id is not None:
        employee = db.get(FaceEmployeeMap, match.employee_map_id)
        if employee is not None:
            employee_id = employee.employee_id
            sync_result = odoo_service.sync_attendance(employee_id=employee.employee_id, action=action)
            sync = OdooAttendanceSync(
                employee_map_id=employee.id,
                attempt_id=attempt.id,
                action=action,
                sync_status="success" if sync_result.success else "failed",
                odoo_attendance_id=sync_result.odoo_attendance_id,
                response_payload=sync_result.response,
                synced_at=datetime.now(timezone.utc),
            )
            db.add(sync)

    attempt.status = "success" if recognition.matched else "failed"
    db.add(attempt)
    db.commit()

    return success_response(
        message=f"Attendance {action} processed",
        code="ATTENDANCE_PROCESSED",
        data={
            "attempt_id": attempt.id,
            "action": action,
            "matched": recognition.matched,
            "employee_id": employee_id,
            "similarity": recognition.similarity,
            "quality_score": attempt.quality_score,
            "status": attempt.status,
        },
    )


@router.post("/checkin")
def checkin(payload: AttendanceRequest, db: Session = Depends(get_db)):
    return _run_attendance(action="checkin", payload=payload, db=db)


@router.post("/checkout")
def checkout(payload: AttendanceRequest, db: Session = Depends(get_db)):
    return _run_attendance(action="checkout", payload=payload, db=db)


@router.get("/history")
def history(
    employee_id: Optional[str] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    attempts = db.scalars(select(FaceAttendanceAttempt).order_by(desc(FaceAttendanceAttempt.id)).limit(limit)).all()

    payload: list[dict] = []
    for attempt in attempts:
        recognition = db.scalar(
            select(FaceRecognitionResult).where(FaceRecognitionResult.attempt_id == attempt.id)
        )

        mapped_employee_id: Optional[str] = None
        if recognition and recognition.employee_map_id:
            employee = db.get(FaceEmployeeMap, recognition.employee_map_id)
            mapped_employee_id = employee.employee_id if employee else None

        if employee_id and mapped_employee_id != employee_id:
            continue

        payload.append(
            {
                "attempt_id": attempt.id,
                "action": attempt.action,
                "captured_at": attempt.captured_at.isoformat() if attempt.captured_at else None,
                "status": attempt.status,
                "face_count": attempt.face_count,
                "quality_score": attempt.quality_score,
                "matched": bool(recognition.matched) if recognition else False,
                "employee_id": mapped_employee_id,
                "similarity": float(recognition.similarity) if recognition else 0.0,
            }
        )

    return success_response(
        message="Attendance history fetched",
        code="ATTENDANCE_HISTORY",
        data={"items": payload, "total": len(payload)},
    )
