"""alter face_sample image_path to text

Revision ID: 20260708_0002
Revises: 20260708_0001
Create Date: 2026-07-08 00:10:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260708_0002"
down_revision = "20260708_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "face_sample",
        "image_path",
        existing_type=sa.String(length=512),
        type_=sa.Text(),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "face_sample",
        "image_path",
        existing_type=sa.Text(),
        type_=sa.String(length=512),
        existing_nullable=True,
    )
