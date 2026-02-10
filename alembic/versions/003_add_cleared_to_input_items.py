"""Add cleared flag to input_items for soft-delete

Revision ID: 003
Revises: 002
Create Date: 2026-02-10
"""

from alembic import op
import sqlalchemy as sa

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "input_items",
        sa.Column("cleared", sa.Boolean, nullable=False, server_default=sa.text("false")),
    )


def downgrade() -> None:
    op.drop_column("input_items", "cleared")
