import uuid
from datetime import date, datetime

from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base


class InputItem(Base):
    __tablename__ = "input_items"
    __table_args__ = (
        Index("idx_input_items_client_date", "client_id", "date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE")
    )
    date: Mapped[date] = mapped_column(Date)
    type: Mapped[str] = mapped_column(String(16))  # "text" | "url" | "image"
    content: Mapped[str] = mapped_column(Text)
    extracted_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extract_error: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    cleared: Mapped[bool] = mapped_column(Boolean, server_default="false", default=False)
    importance: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    include_in_generation: Mapped[bool] = mapped_column(
        Boolean, server_default="true", default=True
    )

    client: Mapped["Client"] = relationship(back_populates="input_items")
    edits: Mapped[list["InputItemEdit"]] = relationship(
        back_populates="item", order_by="InputItemEdit.edited_at"
    )


