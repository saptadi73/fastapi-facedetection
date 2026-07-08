"""create face attendance tables

Revision ID: 20260708_0001
Revises: None
Create Date: 2026-07-08 00:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260708_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "face_employee_map",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("employee_id", sa.String(length=64), nullable=False),
        sa.Column("employee_code", sa.String(length=64), nullable=True),
        sa.Column("employee_name", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_enrolled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_face_employee_map_id", "face_employee_map", ["id"])
    op.create_index("ix_face_employee_map_employee_id", "face_employee_map", ["employee_id"], unique=True)

    op.create_table(
        "face_device",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("device_code", sa.String(length=64), nullable=False),
        sa.Column("device_name", sa.String(length=128), nullable=False),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_face_device_id", "face_device", ["id"])
    op.create_index("ix_face_device_device_code", "face_device", ["device_code"], unique=True)

    op.create_table(
        "face_enrollment",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("employee_map_id", sa.Integer(), sa.ForeignKey("face_employee_map.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_index("ix_face_enrollment_id", "face_enrollment", ["id"])
    op.create_index("ix_face_enrollment_employee_map_id", "face_enrollment", ["employee_map_id"])

    op.create_table(
        "face_sample",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("enrollment_id", sa.Integer(), sa.ForeignKey("face_enrollment.id", ondelete="CASCADE"), nullable=False),
        sa.Column("image_path", sa.Text(), nullable=True),
        sa.Column("blur_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("brightness_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("face_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("detector_confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("accepted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_face_sample_id", "face_sample", ["id"])
    op.create_index("ix_face_sample_enrollment_id", "face_sample", ["enrollment_id"])

    op.create_table(
        "face_template",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("employee_map_id", sa.Integer(), sa.ForeignKey("face_employee_map.id", ondelete="CASCADE"), nullable=False),
        sa.Column("embedding_vector", sa.JSON(), nullable=False),
        sa.Column("vector_norm", sa.Float(), nullable=False, server_default="0"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_face_template_id", "face_template", ["id"])
    op.create_index("ix_face_template_employee_map_id", "face_template", ["employee_map_id"])

    op.create_table(
        "face_attendance_attempt",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("device_id", sa.Integer(), sa.ForeignKey("face_device.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(length=32), nullable=False, server_default="checkin"),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("face_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("quality_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
    )
    op.create_index("ix_face_attendance_attempt_id", "face_attendance_attempt", ["id"])
    op.create_index("ix_face_attendance_attempt_device_id", "face_attendance_attempt", ["device_id"])

    op.create_table(
        "face_detection_result",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("attempt_id", sa.Integer(), sa.ForeignKey("face_attendance_attempt.id", ondelete="CASCADE"), nullable=False),
        sa.Column("detector_name", sa.String(length=64), nullable=False, server_default="mediapipe"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("yaw", sa.Float(), nullable=False, server_default="0"),
        sa.Column("pitch", sa.Float(), nullable=False, server_default="0"),
        sa.Column("roll", sa.Float(), nullable=False, server_default="0"),
        sa.Column("is_valid", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.UniqueConstraint("attempt_id", name="uq_face_detection_result_attempt_id"),
    )
    op.create_index("ix_face_detection_result_id", "face_detection_result", ["id"])
    op.create_index("ix_face_detection_result_attempt_id", "face_detection_result", ["attempt_id"])

    op.create_table(
        "face_recognition_result",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("attempt_id", sa.Integer(), sa.ForeignKey("face_attendance_attempt.id", ondelete="CASCADE"), nullable=False),
        sa.Column("employee_map_id", sa.Integer(), sa.ForeignKey("face_employee_map.id", ondelete="SET NULL"), nullable=True),
        sa.Column("similarity", sa.Float(), nullable=False, server_default="0"),
        sa.Column("threshold", sa.Float(), nullable=False, server_default="0.75"),
        sa.Column("matched", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.UniqueConstraint("attempt_id", name="uq_face_recognition_result_attempt_id"),
    )
    op.create_index("ix_face_recognition_result_id", "face_recognition_result", ["id"])
    op.create_index("ix_face_recognition_result_attempt_id", "face_recognition_result", ["attempt_id"])
    op.create_index("ix_face_recognition_result_employee_map_id", "face_recognition_result", ["employee_map_id"])

    op.create_table(
        "odoo_attendance_sync",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("employee_map_id", sa.Integer(), sa.ForeignKey("face_employee_map.id", ondelete="SET NULL"), nullable=True),
        sa.Column("attempt_id", sa.Integer(), sa.ForeignKey("face_attendance_attempt.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(length=32), nullable=False, server_default="checkin"),
        sa.Column("sync_status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("odoo_attendance_id", sa.String(length=64), nullable=True),
        sa.Column("response_payload", sa.JSON(), nullable=True),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_odoo_attendance_sync_id", "odoo_attendance_sync", ["id"])
    op.create_index("ix_odoo_attendance_sync_employee_map_id", "odoo_attendance_sync", ["employee_map_id"])
    op.create_index("ix_odoo_attendance_sync_attempt_id", "odoo_attendance_sync", ["attempt_id"])

    op.create_table(
        "face_setting",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("key", sa.String(length=128), nullable=False),
        sa.Column("value", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=512), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_face_setting_id", "face_setting", ["id"])
    op.create_index("ix_face_setting_key", "face_setting", ["key"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_face_setting_key", table_name="face_setting")
    op.drop_index("ix_face_setting_id", table_name="face_setting")
    op.drop_table("face_setting")

    op.drop_index("ix_odoo_attendance_sync_attempt_id", table_name="odoo_attendance_sync")
    op.drop_index("ix_odoo_attendance_sync_employee_map_id", table_name="odoo_attendance_sync")
    op.drop_index("ix_odoo_attendance_sync_id", table_name="odoo_attendance_sync")
    op.drop_table("odoo_attendance_sync")

    op.drop_index("ix_face_recognition_result_employee_map_id", table_name="face_recognition_result")
    op.drop_index("ix_face_recognition_result_attempt_id", table_name="face_recognition_result")
    op.drop_index("ix_face_recognition_result_id", table_name="face_recognition_result")
    op.drop_table("face_recognition_result")

    op.drop_index("ix_face_detection_result_attempt_id", table_name="face_detection_result")
    op.drop_index("ix_face_detection_result_id", table_name="face_detection_result")
    op.drop_table("face_detection_result")

    op.drop_index("ix_face_attendance_attempt_device_id", table_name="face_attendance_attempt")
    op.drop_index("ix_face_attendance_attempt_id", table_name="face_attendance_attempt")
    op.drop_table("face_attendance_attempt")

    op.drop_index("ix_face_template_employee_map_id", table_name="face_template")
    op.drop_index("ix_face_template_id", table_name="face_template")
    op.drop_table("face_template")

    op.drop_index("ix_face_sample_enrollment_id", table_name="face_sample")
    op.drop_index("ix_face_sample_id", table_name="face_sample")
    op.drop_table("face_sample")

    op.drop_index("ix_face_enrollment_employee_map_id", table_name="face_enrollment")
    op.drop_index("ix_face_enrollment_id", table_name="face_enrollment")
    op.drop_table("face_enrollment")

    op.drop_index("ix_face_device_device_code", table_name="face_device")
    op.drop_index("ix_face_device_id", table_name="face_device")
    op.drop_table("face_device")

    op.drop_index("ix_face_employee_map_employee_id", table_name="face_employee_map")
    op.drop_index("ix_face_employee_map_id", table_name="face_employee_map")
    op.drop_table("face_employee_map")
