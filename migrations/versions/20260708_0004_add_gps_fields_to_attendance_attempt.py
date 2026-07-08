"""add gps fields to attendance attempt

Revision ID: 20260708_0004
Revises: 20260708_0003
Create Date: 2026-07-08 09:45:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260708_0004"
down_revision = "20260708_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("face_attendance_attempt", sa.Column("latitude", sa.Float(), nullable=True))
    op.add_column("face_attendance_attempt", sa.Column("longitude", sa.Float(), nullable=True))
    op.add_column("face_attendance_attempt", sa.Column("gps_accuracy_meters", sa.Float(), nullable=True))
    op.add_column("face_attendance_attempt", sa.Column("gps_provider", sa.String(length=32), nullable=True))


def downgrade() -> None:
    op.drop_column("face_attendance_attempt", "gps_provider")
    op.drop_column("face_attendance_attempt", "gps_accuracy_meters")
    op.drop_column("face_attendance_attempt", "longitude")
    op.drop_column("face_attendance_attempt", "latitude")
