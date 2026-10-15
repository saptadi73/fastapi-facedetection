"""add attendance context and visit details

Revision ID: 20261015_0007
Revises: 20260923_0006
"""

from alembic import op
import sqlalchemy as sa


revision = "20261015_0007"
down_revision = "20260923_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("face_attendance_attempt", sa.Column("attendance_context", sa.String(length=32), nullable=False, server_default="office"))
    op.add_column("face_attendance_attempt", sa.Column("visit_partner", sa.String(length=255), nullable=True))
    op.add_column("face_attendance_attempt", sa.Column("visit_note", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("face_attendance_attempt", "visit_note")
    op.drop_column("face_attendance_attempt", "visit_partner")
    op.drop_column("face_attendance_attempt", "attendance_context")
