import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base


class PublishedPost(Base):
    __tablename__ = "published_posts"
    __table_args__ = (
        Index("idx_published_posts_published_at", "published_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    generation_result_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("generation_results.id", ondelete="CASCADE"),
        unique=True,
        nullable=True,
    )
    input_item_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("input_items.id", ondelete="CASCADE"),
        nullable=True,
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE")
    )
    slug: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    generation_result: Mapped[Optional["GenerationResult"]] = relationship()
    input_item: Mapped[Optional["InputItem"]] = relationship()
    client: Mapped["Client"] = relationship()
