"""create face sample storage table

Revision ID: 20260708_0003
Revises: 20260708_0002
Create Date: 2026-07-08 09:20:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260708_0003"
down_revision = "20260708_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "face_sample_storage",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sample_id", sa.Integer(), sa.ForeignKey("face_sample.id", ondelete="CASCADE"), nullable=False),
        sa.Column("storage_target", sa.String(length=32), nullable=False, server_default="local"),
        sa.Column("storage_path", sa.Text(), nullable=True),
        sa.Column("storage_url", sa.Text(), nullable=True),
        sa.Column("external_id", sa.String(length=128), nullable=True),
        sa.Column("sync_status", sa.String(length=32), nullable=False, server_default="success"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_face_sample_storage_id", "face_sample_storage", ["id"])
    op.create_index("ix_face_sample_storage_sample_id", "face_sample_storage", ["sample_id"])


def downgrade() -> None:
    op.drop_index("ix_face_sample_storage_sample_id", table_name="face_sample_storage")
    op.drop_index("ix_face_sample_storage_id", table_name="face_sample_storage")
    op.drop_table("face_sample_storage")
