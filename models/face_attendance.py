from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from config.database import Base


class EnrollmentStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class AttendanceAction(str, Enum):
    CHECKIN = "checkin"
    CHECKOUT = "checkout"


class SyncStatus(str, Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"


class StorageTarget(str, Enum):
    LOCAL = "local"
    OBJECT = "object"
    ODOO = "odoo"


class FaceEmployeeMap(Base):
    __tablename__ = "face_employee_map"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    employee_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    employee_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    employee_name: Mapped[str] = mapped_column(String(255))
    odoo_user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    login_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_enrolled: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    enrollments: Mapped[list[FaceEnrollment]] = relationship(back_populates="employee_map")
    templates: Mapped[list[FaceTemplate]] = relationship(back_populates="employee_map")
    recognition_results: Mapped[list[FaceRecognitionResult]] = relationship(back_populates="employee_map")
    sync_logs: Mapped[list[OdooAttendanceSync]] = relationship(back_populates="employee_map")


class FaceEnrollment(Base):
    __tablename__ = "face_enrollment"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    employee_map_id: Mapped[int] = mapped_column(ForeignKey("face_employee_map.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(32), default=EnrollmentStatus.PENDING.value)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    employee_map: Mapped[FaceEmployeeMap] = relationship(back_populates="enrollments")
    samples: Mapped[list[FaceSample]] = relationship(back_populates="enrollment")


class FaceSample(Base):
    __tablename__ = "face_sample"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    enrollment_id: Mapped[int] = mapped_column(ForeignKey("face_enrollment.id", ondelete="CASCADE"), index=True)
    image_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    blur_score: Mapped[float] = mapped_column(Float, default=0)
    brightness_score: Mapped[float] = mapped_column(Float, default=0)
    face_count: Mapped[int] = mapped_column(Integer, default=0)
    detector_confidence: Mapped[float] = mapped_column(Float, default=0)
    accepted: Mapped[bool] = mapped_column(Boolean, default=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    enrollment: Mapped[FaceEnrollment] = relationship(back_populates="samples")
    storage_items: Mapped[list[FaceSampleStorage]] = relationship(back_populates="sample")


class FaceSampleStorage(Base):
    __tablename__ = "face_sample_storage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    sample_id: Mapped[int] = mapped_column(ForeignKey("face_sample.id", ondelete="CASCADE"), index=True)
    storage_target: Mapped[str] = mapped_column(String(32), default=StorageTarget.LOCAL.value)
    storage_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    storage_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    external_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    sync_status: Mapped[str] = mapped_column(String(32), default=SyncStatus.SUCCESS.value)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    sample: Mapped[FaceSample] = relationship(back_populates="storage_items")


class FaceTemplate(Base):
    __tablename__ = "face_template"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    employee_map_id: Mapped[int] = mapped_column(ForeignKey("face_employee_map.id", ondelete="CASCADE"), index=True)
    embedding_vector: Mapped[list[float]] = mapped_column(JSON)
    vector_norm: Mapped[float] = mapped_column(Float, default=0)
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    employee_map: Mapped[FaceEmployeeMap] = relationship(back_populates="templates")


class FaceAttendanceAttempt(Base):
    __tablename__ = "face_attendance_attempt"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    device_id: Mapped[Optional[int]] = mapped_column(ForeignKey("face_device.id", ondelete="SET NULL"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(32), default=AttendanceAction.CHECKIN.value)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    gps_accuracy_meters: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    gps_provider: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    face_count: Mapped[int] = mapped_column(Integer, default=0)
    quality_score: Mapped[float] = mapped_column(Float, default=0)
    status: Mapped[str] = mapped_column(String(32), default=SyncStatus.PENDING.value)

    device: Mapped[Optional[FaceDevice]] = relationship(back_populates="attempts")
    detection_result: Mapped[Optional[FaceDetectionResult]] = relationship(back_populates="attempt", uselist=False)
    recognition_result: Mapped[Optional[FaceRecognitionResult]] = relationship(back_populates="attempt", uselist=False)
    sync_logs: Mapped[list[OdooAttendanceSync]] = relationship(back_populates="attempt")


class FaceDetectionResult(Base):
    __tablename__ = "face_detection_result"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    attempt_id: Mapped[int] = mapped_column(ForeignKey("face_attendance_attempt.id", ondelete="CASCADE"), unique=True, index=True)
    detector_name: Mapped[str] = mapped_column(String(64), default="mediapipe")
    confidence: Mapped[float] = mapped_column(Float, default=0)
    yaw: Mapped[float] = mapped_column(Float, default=0)
    pitch: Mapped[float] = mapped_column(Float, default=0)
    roll: Mapped[float] = mapped_column(Float, default=0)
    is_valid: Mapped[bool] = mapped_column(Boolean, default=False)

    attempt: Mapped[FaceAttendanceAttempt] = relationship(back_populates="detection_result")


class FaceRecognitionResult(Base):
    __tablename__ = "face_recognition_result"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    attempt_id: Mapped[int] = mapped_column(ForeignKey("face_attendance_attempt.id", ondelete="CASCADE"), unique=True, index=True)
    employee_map_id: Mapped[Optional[int]] = mapped_column(ForeignKey("face_employee_map.id", ondelete="SET NULL"), nullable=True, index=True)
    similarity: Mapped[float] = mapped_column(Float, default=0)
    threshold: Mapped[float] = mapped_column(Float, default=0.75)
    matched: Mapped[bool] = mapped_column(Boolean, default=False)

    attempt: Mapped[FaceAttendanceAttempt] = relationship(back_populates="recognition_result")
    employee_map: Mapped[Optional[FaceEmployeeMap]] = relationship(back_populates="recognition_results")


class OdooAttendanceSync(Base):
    __tablename__ = "odoo_attendance_sync"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    employee_map_id: Mapped[Optional[int]] = mapped_column(ForeignKey("face_employee_map.id", ondelete="SET NULL"), nullable=True, index=True)
    attempt_id: Mapped[Optional[int]] = mapped_column(ForeignKey("face_attendance_attempt.id", ondelete="SET NULL"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(32), default=AttendanceAction.CHECKIN.value)
    sync_status: Mapped[str] = mapped_column(String(32), default=SyncStatus.PENDING.value)
    odoo_attendance_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    response_payload: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    employee_map: Mapped[Optional[FaceEmployeeMap]] = relationship(back_populates="sync_logs")
    attempt: Mapped[Optional[FaceAttendanceAttempt]] = relationship(back_populates="sync_logs")


class FaceDevice(Base):
    __tablename__ = "face_device"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    device_code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    device_name: Mapped[str] = mapped_column(String(128))
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    attempts: Mapped[list[FaceAttendanceAttempt]] = relationship(back_populates="device")


class FaceSetting(Base):
    __tablename__ = "face_setting"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    key: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    value: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
