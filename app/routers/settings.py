import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies import get_client_id
from app.models.channel_setting import ChannelSetting
from app.schemas.settings import (
    ChannelSettingResponse,
    ChannelSettingsRequest,
)

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/channels", response_model=list[ChannelSettingResponse])
async def get_channel_settings(
    client_id: uuid.UUID = Depends(get_client_id),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(ChannelSetting).where(ChannelSetting.client_id == client_id)
    )
    return result.scalars().all()


@router.post("/channels", response_model=list[ChannelSettingResponse])
async def save_channel_settings(
    body: ChannelSettingsRequest,
    client_id: uuid.UUID = Depends(get_client_id),
    session: AsyncSession = Depends(get_session),
):
    # Load existing
    result = await session.execute(
        select(ChannelSetting).where(ChannelSetting.client_id == client_id)
    )
    existing = {cs.channel_id: cs for cs in result.scalars().all()}

    for item in body.channels:
        if item.channel_id in existing:
            cs = existing[item.channel_id]
            cs.is_active = item.is_active
            cs.default_style = item.default_style
            cs.default_language = item.default_language
            cs.default_length = item.default_length
        else:
            cs = ChannelSetting(
                client_id=client_id,
                channel_id=item.channel_id,
                is_active=item.is_active,
                default_style=item.default_style,
                default_language=item.default_language,
                default_length=item.default_length,
            )
            session.add(cs)

    await session.commit()

    # Return all
    result = await session.execute(
        select(ChannelSetting).where(ChannelSetting.client_id == client_id)
    )
    return result.scalars().all()
