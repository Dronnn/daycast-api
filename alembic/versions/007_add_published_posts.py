"""Add published_posts table

Revision ID: 007
Revises: 006
Create Date: 2026-02-10
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "published_posts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "generation_result_id",
            UUID(as_uuid=True),
            sa.ForeignKey("generation_results.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
        ),
        sa.Column(
            "client_id",
            UUID(as_uuid=True),
            sa.ForeignKey("clients.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("slug", sa.Text, unique=True, nullable=False),
        sa.Column(
            "published_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "idx_published_posts_published_at",
        "published_posts",
        [sa.text("published_at DESC")],
    )


def downgrade() -> None:
    op.drop_index("idx_published_posts_published_at", table_name="published_posts")
    op.drop_table("published_posts")
