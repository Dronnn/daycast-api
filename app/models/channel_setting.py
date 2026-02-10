import uuid

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base


class ChannelSetting(Base):
    __tablename__ = "channel_settings"
    __table_args__ = (
        UniqueConstraint("client_id", "channel_id", name="uq_channel_settings_client_channel"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE")
    )
    channel_id: Mapped[str] = mapped_column(String(32))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    default_style: Mapped[str] = mapped_column(String(32), default="casual")
    default_language: Mapped[str] = mapped_column(String(8), default="ru")
    default_length: Mapped[str] = mapped_column(String(16), default="medium")

    client: Mapped["Client"] = relationship(back_populates="channel_settings")


