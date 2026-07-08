from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from models.face_attendance import FaceAttendanceAttempt


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
                )
            )
            .order_by(FaceAttendanceAttempt.id.desc())
            .limit(1)
        )

        last_attempt = db.scalar(stmt)
        return last_attempt is not None and employee_map_id > 0


attendance_service = AttendanceService()
