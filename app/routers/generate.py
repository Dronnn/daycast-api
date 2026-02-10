import uuid

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_session
from app.dependencies import get_client_id
from app.models.channel_setting import ChannelSetting
from app.models.generation import Generation
from app.models.generation_result import GenerationResult
from app.models.input_item import InputItem
from app.schemas.generation import GenerateRequest, GenerationResponse, RegenerateRequest
from app.services.ai import generate, regenerate as ai_regenerate
from app.rate_limit import check_generation_rate_limit
from app.services.product_config import get_channels

router = APIRouter(tags=["generate"])


@router.post("/generate", response_model=GenerationResponse, status_code=201)
async def create_generation(
    body: GenerateRequest,
    _rate: None = Depends(check_generation_rate_limit),
    client_id: uuid.UUID = Depends(get_client_id),
    session: AsyncSession = Depends(get_session),
):
    # 1. Load input items for the date (exclude cleared/deleted)
    result = await session.execute(
        select(InputItem)
        .where(
            InputItem.client_id == client_id,
            InputItem.date == body.date,
            InputItem.cleared == False,
        )
        .order_by(InputItem.created_at)
    )
    items = result.scalars().all()
    if not items:
        raise HTTPException(status_code=400, detail="No input items for this date")

    # 2. Determine target channels
    all_channels = get_channels()
    cs_result = await session.execute(
        select(ChannelSetting).where(ChannelSetting.client_id == client_id)
    )
    cs_rows = cs_result.scalars().all()
    cs_map = {cs.channel_id: cs for cs in cs_rows}

    if body.channels:
        for ch in body.channels:
            if ch not in all_channels:
                raise HTTPException(
                    status_code=400, detail=f"Unknown channel: {ch}"
                )
        channel_ids = body.channels
    else:
        # All active channels (default: all if no settings exist)
        if cs_map:
            channel_ids = [
                ch_id for ch_id, cs in cs_map.items() if cs.is_active
            ]
        else:
            channel_ids = list(all_channels.keys())

    if not channel_ids:
        raise HTTPException(status_code=400, detail="No active channels")

    # 3. Build channel settings dict for AI
    channel_settings = {
        ch_id: {
            "default_style": cs.default_style,
            "default_language": cs.default_language,
            "default_length": cs.default_length,
        }
        for ch_id, cs in cs_map.items()
    }

    # 4. Serialize items for AI service
    items_data = [
        {
            "type": item.type,
            "content": item.content,
            "extracted_text": item.extracted_text,
        }
        for item in items
    ]

    # 5. Call AI
    try:
        ai_results, model_used, latency_ms = await generate(
            items=items_data,
            channel_ids=channel_ids,
            style_override=body.style_override,
            language_override=body.language_override,
            channel_settings=channel_settings,
        )
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail="AI provider error") from e
    except ValueError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    # 6. Save generation + results
    generation = Generation(
        client_id=client_id,
        date=body.date,
        prompt_version="generate_v1",
    )
    session.add(generation)
    await session.flush()  # get generation.id

    for ai_r in ai_results:
        ch_id = ai_r["channel_id"]
        cs = cs_map.get(ch_id, None)
        style = body.style_override or (cs.default_style if cs else "casual")
        language = body.language_override or (cs.default_language if cs else "ru")
        gr = GenerationResult(
            generation_id=generation.id,
            channel_id=ch_id,
            style=style,
            language=language,
            text=ai_r["text"],
            model=model_used,
            latency_ms=latency_ms,
        )
        session.add(gr)

    await session.commit()

    # 7. Reload with results for response
    result = await session.execute(
        select(Generation)
        .where(Generation.id == generation.id)
        .options(selectinload(Generation.results))
    )
    generation = result.scalar_one()
    return generation


@router.post(
    "/generate/{generation_id}/regenerate",
    response_model=GenerationResponse,
    status_code=201,
)
async def regenerate_generation(
    generation_id: uuid.UUID,
    body: RegenerateRequest,
    _rate: None = Depends(check_generation_rate_limit),
    client_id: uuid.UUID = Depends(get_client_id),
    session: AsyncSession = Depends(get_session),
):
    # 1. Load original generation with results
    result = await session.execute(
        select(Generation)
        .where(Generation.id == generation_id, Generation.client_id == client_id)
        .options(selectinload(Generation.results))
    )
    original = result.scalar_one_or_none()
    if original is None:
        raise HTTPException(status_code=404, detail="Generation not found")

    # 2. Load input items for the same date (exclude cleared/deleted)
    items_result = await session.execute(
        select(InputItem)
        .where(
            InputItem.client_id == client_id,
            InputItem.date == original.date,
            InputItem.cleared == False,
        )
        .order_by(InputItem.created_at)
    )
    items = items_result.scalars().all()
    if not items:
        raise HTTPException(status_code=400, detail="No input items for this date")

    # 3. Determine channels
    all_channels = get_channels()
    if body.channels:
        for ch in body.channels:
            if ch not in all_channels:
                raise HTTPException(status_code=400, detail=f"Unknown channel: {ch}")
        channel_ids = body.channels
    else:
        channel_ids = [r.channel_id for r in original.results]

    # 4. Load channel settings
    cs_result = await session.execute(
        select(ChannelSetting).where(ChannelSetting.client_id == client_id)
    )
    cs_map = {cs.channel_id: cs for cs in cs_result.scalars().all()}
    channel_settings = {
        ch_id: {
            "default_style": cs.default_style,
            "default_language": cs.default_language,
            "default_length": cs.default_length,
        }
        for ch_id, cs in cs_map.items()
    }

    # 5. Serialize
    items_data = [
        {
            "type": item.type,
            "content": item.content,
            "extracted_text": item.extracted_text,
        }
        for item in items
    ]
    previous_results = [
        {"channel_id": r.channel_id, "text": r.text}
        for r in original.results
        if r.channel_id in channel_ids
    ]

    # 6. Call AI
    try:
        ai_results, model_used, latency_ms = await ai_regenerate(
            items=items_data,
            channel_ids=channel_ids,
            previous_results=previous_results,
            style_override=None,
            language_override=None,
            channel_settings=channel_settings,
        )
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail="AI provider error") from e
    except ValueError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    # 7. Save new generation
    new_gen = Generation(
        client_id=client_id,
        date=original.date,
        prompt_version="regenerate_v1",
    )
    session.add(new_gen)
    await session.flush()

    for ai_r in ai_results:
        ch_id = ai_r["channel_id"]
        cs = cs_map.get(ch_id, None)
        style = cs.default_style if cs else "casual"
        language = cs.default_language if cs else "ru"
        gr = GenerationResult(
            generation_id=new_gen.id,
            channel_id=ch_id,
            style=style,
            language=language,
            text=ai_r["text"],
            model=model_used,
            latency_ms=latency_ms,
        )
        session.add(gr)

    await session.commit()

    result = await session.execute(
        select(Generation)
        .where(Generation.id == new_gen.id)
        .options(selectinload(Generation.results))
    )
    return result.scalar_one()
