"""add idempotency event id to attendance attempts

Revision ID: 20260923_0006
Revises: 20260709_0005
Create Date: 2026-09-23 00:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260923_0006"
down_revision = "20260709_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("face_attendance_attempt", sa.Column("event_id", sa.String(length=128), nullable=True))
    op.create_index(
        "ix_face_attendance_attempt_event_id",
        "face_attendance_attempt",
        ["event_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_face_attendance_attempt_event_id", table_name="face_attendance_attempt")
    op.drop_column("face_attendance_attempt", "event_id")
