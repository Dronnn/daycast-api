"""Add default_length to channel_settings

Revision ID: 005
Revises: 004
Create Date: 2026-02-10
"""

from alembic import op
import sqlalchemy as sa

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "channel_settings",
        sa.Column("default_length", sa.String(16), nullable=False, server_default="medium"),
    )


def downgrade() -> None:
    op.drop_column("channel_settings", "default_length")
