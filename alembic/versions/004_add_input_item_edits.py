"""Add input_item_edits table for edit history tracking

Revision ID: 004
Revises: 003
Create Date: 2026-02-10
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "input_item_edits",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("item_id", UUID(as_uuid=True), sa.ForeignKey("input_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("old_content", sa.Text, nullable=False),
        sa.Column("edited_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_input_item_edits_item_id", "input_item_edits", ["item_id"])


def downgrade() -> None:
    op.drop_index("idx_input_item_edits_item_id")
    op.drop_table("input_item_edits")
