"""Add extracted_text and extract_error to input_items

Revision ID: 002
Revises: 001
Create Date: 2025-02-10
"""

from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("input_items", sa.Column("extracted_text", sa.Text, nullable=True))
    op.add_column(
        "input_items", sa.Column("extract_error", sa.String(512), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("input_items", "extract_error")
    op.drop_column("input_items", "extracted_text")
