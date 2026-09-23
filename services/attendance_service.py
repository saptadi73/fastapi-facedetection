from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from models.face_attendance import (
    FaceAttendanceAttempt,
    FaceEmployeeMap,
    FaceRecognitionResult,
    OdooAttendanceSync,
)
from services.embedding_service import embedding_service
from services.odoo_service import odoo_service


class AttendanceService:
    def is_duplicate_attempt(
        self,
        db: Session,
        employee_map_id: int,
        action: str,
        window_seconds: int = 60,
    ) -> bool:
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(seconds=window_seconds)

        stmt = (
            select(FaceAttendanceAttempt)
            .where(
                and_(
                    FaceAttendanceAttempt.captured_at >= window_start,
                    FaceAttendanceAttempt.action == action,
                    FaceAttendanceAttempt.status == "success",
                    FaceRecognitionResult.employee_map_id == employee_map_id,
                )
            )
            .join(FaceRecognitionResult, FaceRecognitionResult.attempt_id == FaceAttendanceAttempt.id)
            .order_by(FaceAttendanceAttempt.id.desc())
            .limit(1)
        )

        last_attempt = db.scalar(stmt)
        return last_attempt is not None and employee_map_id > 0

    def retry_failed_syncs(self, db: Session, limit: int = 20) -> dict:
        """Replay failed Odoo sync rows without creating a second local attempt."""
        rows = db.scalars(
            select(OdooAttendanceSync)
            .where(OdooAttendanceSync.sync_status == "failed")
            .order_by(OdooAttendanceSync.id.asc())
            .limit(limit)
        ).all()

        results: list[dict] = []
        for sync in rows:
            attempt = db.get(FaceAttendanceAttempt, sync.attempt_id) if sync.attempt_id else None
            employee = db.get(FaceEmployeeMap, sync.employee_map_id) if sync.employee_map_id else None
            recognition = (
                db.scalar(select(FaceRecognitionResult).where(FaceRecognitionResult.attempt_id == attempt.id))
                if attempt
                else None
            )
            if not attempt or not employee or not recognition:
                results.append({"sync_id": sync.id, "success": False, "error": "Missing attendance context"})
                continue

            retry_result = odoo_service.sync_attendance(
                employee_id=employee.employee_id,
                action=sync.action,
                attendance_context={
                    "attempt_id": attempt.id,
                    "captured_at": attempt.captured_at.isoformat() if attempt.captured_at else None,
                    "similarity": recognition.similarity,
                    "embedding_provider": embedding_service.provider_name(),
                    "quality_score": attempt.quality_score,
                    "latitude": attempt.latitude,
                    "longitude": attempt.longitude,
                    "gps_accuracy_meters": attempt.gps_accuracy_meters,
                    "gps_provider": attempt.gps_provider,
                },
            )
            sync.sync_status = "success" if retry_result.success else "failed"
            sync.odoo_attendance_id = retry_result.odoo_attendance_id
            sync.response_payload = retry_result.response
            sync.synced_at = datetime.now(timezone.utc) if retry_result.success else None
            attempt.status = "success" if retry_result.success else "failed"
            results.append({
                "sync_id": sync.id,
                "attempt_id": attempt.id,
                "success": retry_result.success,
                "odoo_attendance_id": retry_result.odoo_attendance_id,
                "error": None if retry_result.success else retry_result.response.get("error"),
            })

        db.commit()
        return {"items": results, "total": len(results), "succeeded": sum(item["success"] for item in results)}


attendance_service = AttendanceService()
