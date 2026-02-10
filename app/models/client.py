import uuid
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    input_items: Mapped[list["InputItem"]] = relationship(back_populates="client")
    generations: Mapped[list["Generation"]] = relationship(back_populates="client")
    channel_settings: Mapped[list["ChannelSetting"]] = relationship(
        back_populates="client"
    )


