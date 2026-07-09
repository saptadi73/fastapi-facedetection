from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from config.database import get_db
from models.face_attendance import FaceEmployeeMap, FaceEnrollment, FaceSample, FaceSampleStorage, FaceTemplate
from schemas.face_enrollment import (
    EnrollmentFinishRequest,
    EnrollmentSampleRequest,
    EnrollmentStartRequest,
)
from services.embedding_service import embedding_service
from services.faiss_service import faiss_service
from services.face_quality_service import face_quality_service
from services.image_service import image_service
from services.local_storage_service import local_storage_service
from services.mediapipe_service import mediapipe_service
from services.sample_media_storage_service import sample_media_storage_service
from supports import error_response, success_response

router = APIRouter(prefix="/api/v1/face/enroll", tags=["Face Enrollment"])


@router.post("/start")
def start_enrollment(payload: EnrollmentStartRequest, db: Session = Depends(get_db)):
    employee = db.scalar(select(FaceEmployeeMap).where(FaceEmployeeMap.employee_id == payload.employee_id))
    if employee is None:
        employee = FaceEmployeeMap(
            employee_id=payload.employee_id,
            employee_code=payload.employee_code,
            employee_name=payload.employee_name,
            is_active=True,
            is_enrolled=False,
        )
        db.add(employee)
        db.flush()

    enrollment = FaceEnrollment(
        employee_map_id=employee.id,
        status="in_progress",
        started_at=datetime.now(timezone.utc),
    )
    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)

    return success_response(
        message="Enrollment started",
        status_code=201,
        code="ENROLLMENT_STARTED",
        data={
            "enrollment_id": enrollment.id,
            "employee_id": employee.employee_id,
            "status": enrollment.status,
            "started_at": enrollment.started_at.isoformat() if enrollment.started_at else None,
        },
    )


@router.post("/sample")
def upload_enrollment_sample(payload: EnrollmentSampleRequest, db: Session = Depends(get_db)):
    employee = db.scalar(select(FaceEmployeeMap).where(FaceEmployeeMap.employee_id == payload.employee_id))
    if employee is None:
        return error_response(message="Employee not found", status_code=404, code="EMPLOYEE_NOT_FOUND")

    enrollment = db.query(FaceEnrollment).filter(
        FaceEnrollment.employee_map_id == employee.id,
        FaceEnrollment.status == "in_progress"
    ).order_by(desc(FaceEnrollment.id)).first()

    if enrollment is None:
        return error_response(
            message="No active enrollment session",
            status_code=400,
            code="NO_ACTIVE_ENROLLMENT",
        )

    image_bytes = image_service.decode_base64(payload.image_base64)
    image = image_service.open_image(image_bytes)
    quality = image_service.evaluate_quality(image)
    face = mediapipe_service.detect(image.width, image.height)
    quality_decision = face_quality_service.evaluate(face=face, quality=quality)

    sample = FaceSample(
        enrollment_id=enrollment.id,
        image_path=None,
        blur_score=quality.blur_score,
        brightness_score=quality.brightness_score,
        face_count=face.face_count,
        detector_confidence=face.confidence,
        accepted=quality_decision.accepted,
        captured_at=datetime.now(timezone.utc),
    )
    db.add(sample)
    db.flush()

    storage_result = sample_media_storage_service.store_all(
        employee_id=employee.employee_id,
        sample_id=sample.id,
        image_bytes=image_bytes,
    )

    sample.image_path = storage_result.local_path
    local_url = "/" + Path(storage_result.local_path).as_posix()

    db.add_all(
        [
            FaceSampleStorage(
                sample_id=sample.id,
                storage_target="local",
                storage_path=storage_result.local_path,
                storage_url=local_url,
                external_id=None,
                sync_status="success",
            ),
            FaceSampleStorage(
                sample_id=sample.id,
                storage_target="object",
                storage_path=None,
                storage_url=storage_result.object_url,
                external_id=None,
                sync_status="success",
            ),
            FaceSampleStorage(
                sample_id=sample.id,
                storage_target="odoo",
                storage_path=None,
                storage_url=None,
                external_id=storage_result.odoo_attachment_id,
                sync_status="success" if storage_result.odoo_attachment_id else "failed",
            ),
        ]
    )

    db.commit()
    db.refresh(sample)

    return success_response(
        message="Sample saved",
        status_code=201,
        code="SAMPLE_SAVED",
        data={
            "sample_id": sample.id,
            "accepted": sample.accepted,
            "reason_codes": quality_decision.reason_codes,
            "blur_score": sample.blur_score,
            "brightness_score": sample.brightness_score,
            "face_count": sample.face_count,
            "detector_confidence": sample.detector_confidence,
            "storage": {
                "local_path": storage_result.local_path,
                "local_url": local_url,
                "object_url": storage_result.object_url,
                "odoo_attachment_id": storage_result.odoo_attachment_id,
            },
        },
    )


@router.post("/finish")
def finish_enrollment(payload: EnrollmentFinishRequest, db: Session = Depends(get_db)):
    employee = db.scalar(select(FaceEmployeeMap).where(FaceEmployeeMap.employee_id == payload.employee_id))
    if employee is None:
        return error_response(message="Employee not found", status_code=404, code="EMPLOYEE_NOT_FOUND")

    enrollment = db.scalar(
        select(FaceEnrollment)
        .where(FaceEnrollment.employee_map_id == employee.id)
        .order_by(desc(FaceEnrollment.id))
        .limit(1)
    )
    if enrollment is None or enrollment.status != "in_progress":
        return error_response(message="No active enrollment session", code="NO_ACTIVE_ENROLLMENT")

    accepted_samples = db.scalar(
        select(func.count(FaceSample.id)).where(
            FaceSample.enrollment_id == enrollment.id,
            FaceSample.accepted.is_(True),
        )
    )
    accepted_samples = int(accepted_samples or 0)

    if accepted_samples < 5:
        return error_response(
            message="Not enough accepted samples. Minimum is 5.",
            status_code=422,
            code="INSUFFICIENT_SAMPLES",
            data={"accepted_samples": accepted_samples},
        )

    valid_samples = db.scalars(
        select(FaceSample)
        .where(
            FaceSample.enrollment_id == enrollment.id,
            FaceSample.accepted.is_(True),
        )
        .order_by(FaceSample.id)
    ).all()
    if not valid_samples:
        return error_response(
            message="No valid accepted sample found for embedding",
            status_code=422,
            code="NO_VALID_SAMPLE",
        )

    db.query(FaceTemplate).filter(FaceTemplate.employee_map_id == employee.id).update({"is_active": False})
    faiss_service.remove_embedding(employee.id)

    created_templates: list[FaceTemplate] = []
    for sample in valid_samples:
        if not sample.image_path:
            continue
        try:
            sample_bytes = local_storage_service.read_image(sample.image_path)
        except Exception:
            # Backward compatibility for old records that still contain base64 payload.
            sample_bytes = image_service.decode_base64(sample.image_path)
        embedding = embedding_service.generate_embedding(sample_bytes)
        template = FaceTemplate(
            employee_map_id=employee.id,
            embedding_vector=embedding,
            vector_norm=1.0,
            version=1,
            is_active=True,
        )
        db.add(template)
        created_templates.append(template)

    if not created_templates:
        return error_response(
            message="No readable accepted sample found for embedding",
            status_code=422,
            code="NO_READABLE_SAMPLE",
        )

    db.flush()
    for template in created_templates:
        faiss_service.add_embedding(employee.id, template.embedding_vector, template_id=template.id)

    enrollment.status = "completed"
    enrollment.finished_at = datetime.now(timezone.utc)
    enrollment.notes = payload.notes
    employee.is_enrolled = True

    db.add(enrollment)
    db.add(employee)
    db.commit()

    return success_response(
        message="Enrollment completed",
        code="ENROLLMENT_COMPLETED",
        data={
            "employee_id": employee.employee_id,
            "accepted_samples": accepted_samples,
            "templates_created": len(created_templates),
            "embedding_provider": embedding_service.provider_name(),
            "status": enrollment.status,
        },
    )


@router.get("/{employee_id}")
def get_enrollment_status(employee_id: str, db: Session = Depends(get_db)):
    employee = db.scalar(select(FaceEmployeeMap).where(FaceEmployeeMap.employee_id == employee_id))
    if employee is None:
        return error_response(message="Employee not found", status_code=404, code="EMPLOYEE_NOT_FOUND")

    enrollment = db.scalar(
        select(FaceEnrollment)
        .where(FaceEnrollment.employee_map_id == employee.id)
        .order_by(desc(FaceEnrollment.id))
        .limit(1)
    )
    if enrollment is None:
        return success_response(
            message="Enrollment not started",
            code="ENROLLMENT_NOT_STARTED",
            data={
                "employee_id": employee.employee_id,
                "employee_name": employee.employee_name,
                "status": "pending",
                "total_samples": 0,
                "accepted_samples": 0,
                "is_enrolled": employee.is_enrolled,
            },
        )

    total_samples = db.scalar(select(func.count(FaceSample.id)).where(FaceSample.enrollment_id == enrollment.id)) or 0
    accepted_samples = db.scalar(
        select(func.count(FaceSample.id)).where(
            FaceSample.enrollment_id == enrollment.id,
            FaceSample.accepted.is_(True),
        )
    ) or 0

    return success_response(
        message="Enrollment status fetched",
        code="ENROLLMENT_STATUS",
        data={
            "employee_id": employee.employee_id,
            "employee_name": employee.employee_name,
            "status": enrollment.status,
            "total_samples": int(total_samples),
            "accepted_samples": int(accepted_samples),
            "is_enrolled": employee.is_enrolled,
            "started_at": enrollment.started_at.isoformat() if enrollment.started_at else None,
            "finished_at": enrollment.finished_at.isoformat() if enrollment.finished_at else None,
        },
    )
