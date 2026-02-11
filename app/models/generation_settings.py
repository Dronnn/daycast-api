import uuid
from typing import Optional

from sqlalchemy import Boolean, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base


class GenerationSettings(Base):
    __tablename__ = "generation_settings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        unique=True,
    )
    custom_instruction: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    separate_business_personal: Mapped[bool] = mapped_column(
        Boolean, server_default="false", default=False
    )

    client: Mapped["Client"] = relationship()
