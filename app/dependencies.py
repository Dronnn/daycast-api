import uuid

import jwt
from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.client import Client
from app.services.auth import decode_jwt


async def get_client_id(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> uuid.UUID:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing authorization token")

    token = auth_header[7:]
    try:
        user_id = decode_jwt(token)
    except (jwt.PyJWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    # Ensure client record exists
    result = await session.execute(select(Client).where(Client.id == user_id))
    if result.scalar_one_or_none() is None:
        client = Client(id=user_id)
        session.add(client)
        await session.commit()

    return user_id
