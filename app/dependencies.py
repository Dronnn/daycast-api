import uuid

from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.client import Client

# Single shared client ID for all devices (AUTH_MODE=none, personal use)
SHARED_CLIENT_ID = uuid.UUID("00000000-0000-4000-a000-000000000001")


async def get_client_id(
    x_client_id: uuid.UUID = Header(default=None),
    session: AsyncSession = Depends(get_session),
) -> uuid.UUID:
    # Ignore per-device client_id, always use shared one
    client_id = SHARED_CLIENT_ID
    result = await session.execute(select(Client).where(Client.id == client_id))
    client = result.scalar_one_or_none()
    if client is None:
        client = Client(id=client_id)
        session.add(client)
        await session.commit()
    return client_id
