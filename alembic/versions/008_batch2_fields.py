"""Batch 2: importance, include_in_generation, generation_settings, published_posts input_item support

Revision ID: 008
Revises: 007
Create Date: 2026-02-11
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # input_items: importance (1-5) and include_in_generation flag
    op.add_column("input_items", sa.Column("importance", sa.Integer, nullable=True))
    op.add_column(
        "input_items",
        sa.Column(
            "include_in_generation",
            sa.Boolean,
            nullable=False,
            server_default="true",
        ),
    )

    # generation_settings: per-client AI generation preferences
    op.create_table(
        "generation_settings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "client_id",
            UUID(as_uuid=True),
            sa.ForeignKey("clients.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("custom_instruction", sa.Text, nullable=True),
        sa.Column(
            "separate_business_personal",
            sa.Boolean,
            nullable=False,
            server_default="false",
        ),
    )

    # published_posts: support publishing InputItem directly
    op.alter_column(
        "published_posts",
        "generation_result_id",
        existing_type=UUID(as_uuid=True),
        nullable=True,
    )
    op.add_column(
        "published_posts",
        sa.Column(
            "input_item_id",
            UUID(as_uuid=True),
            sa.ForeignKey("input_items.id", ondelete="CASCADE"),
            nullable=True,
        ),
    )
    op.add_column(
        "published_posts",
        sa.Column("text", sa.Text, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("published_posts", "text")
    op.drop_column("published_posts", "input_item_id")
    op.alter_column(
        "published_posts",
        "generation_result_id",
        existing_type=UUID(as_uuid=True),
        nullable=False,
    )
    op.drop_table("generation_settings")
    op.drop_column("input_items", "include_in_generation")
    op.drop_column("input_items", "importance")
