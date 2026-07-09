"""add odoo user fields to employee map

Revision ID: 20260709_0005
Revises: 20260708_0004
Create Date: 2026-07-09 10:45:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260709_0005"
down_revision = "20260708_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("face_employee_map", sa.Column("odoo_user_id", sa.Integer(), nullable=True))
    op.add_column("face_employee_map", sa.Column("login_email", sa.String(length=255), nullable=True))
    op.create_index("ix_face_employee_map_odoo_user_id", "face_employee_map", ["odoo_user_id"])
    op.create_index("ix_face_employee_map_login_email", "face_employee_map", ["login_email"])


def downgrade() -> None:
    op.drop_index("ix_face_employee_map_login_email", table_name="face_employee_map")
    op.drop_index("ix_face_employee_map_odoo_user_id", table_name="face_employee_map")
    op.drop_column("face_employee_map", "login_email")
    op.drop_column("face_employee_map", "odoo_user_id")
