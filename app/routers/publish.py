import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_session
from app.dependencies import get_client_id
from app.models.generation import Generation
from app.models.generation_result import GenerationResult
from app.models.input_item import InputItem
from app.models.published_post import PublishedPost
from app.schemas.publish import (
    PublishRequest,
    PublishedPostResponse,
    PublishStatusResponse,
)

router = APIRouter(prefix="/publish", tags=["publish"])


def _build_response(
    post: PublishedPost,
    result: GenerationResult,
    generation: Generation,
    input_items: list[InputItem],
) -> PublishedPostResponse:
    preview = [
        item.content[:80] for item in input_items[:5] if not item.cleared
    ]
    return PublishedPostResponse(
        id=post.id,
        slug=post.slug,
        channel_id=result.channel_id,
        style=result.style,
        language=result.language,
        text=result.text,
        date=generation.date,
        published_at=post.published_at,
        input_items_preview=preview,
    )


@router.post("", response_model=PublishedPostResponse, status_code=201)
async def publish_post(
    body: PublishRequest,
    client_id: uuid.UUID = Depends(get_client_id),
    session: AsyncSession = Depends(get_session),
):
    # Validate the result belongs to current user
    result = await session.execute(
        select(GenerationResult)
        .join(Generation, GenerationResult.generation_id == Generation.id)
        .where(
            GenerationResult.id == body.generation_result_id,
            Generation.client_id == client_id,
        )
    )
    gen_result = result.scalar_one_or_none()
    if gen_result is None:
        raise HTTPException(status_code=404, detail="Generation result not found")

    # Check not already published
    existing = await session.execute(
        select(PublishedPost).where(
            PublishedPost.generation_result_id == body.generation_result_id
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Already published")

    # Load generation for date
    gen_row = await session.execute(
        select(Generation).where(Generation.id == gen_result.generation_id)
    )
    generation = gen_row.scalar_one()

    # Generate slug
    slug = f"{generation.date}-{gen_result.channel_id}-{uuid.uuid4().hex[:4]}"

    post = PublishedPost(
        generation_result_id=body.generation_result_id,
        client_id=client_id,
        slug=slug,
    )
    session.add(post)
    await session.commit()
    await session.refresh(post)

    # Load input items for preview
    items_result = await session.execute(
        select(InputItem)
        .where(
            InputItem.client_id == client_id,
            InputItem.date == generation.date,
            InputItem.cleared == False,
        )
        .order_by(InputItem.created_at)
    )
    input_items = items_result.scalars().all()

    return _build_response(post, gen_result, generation, list(input_items))


@router.delete("/{post_id}", status_code=204)
async def unpublish_post(
    post_id: uuid.UUID,
    client_id: uuid.UUID = Depends(get_client_id),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(PublishedPost).where(
            PublishedPost.id == post_id,
            PublishedPost.client_id == client_id,
        )
    )
    post = result.scalar_one_or_none()
    if post is None:
        raise HTTPException(status_code=404, detail="Published post not found")

    await session.delete(post)
    await session.commit()


@router.get("/status", response_model=PublishStatusResponse)
async def get_publish_status(
    result_ids: str,
    client_id: uuid.UUID = Depends(get_client_id),
    session: AsyncSession = Depends(get_session),
):
    ids = [uuid.UUID(rid.strip()) for rid in result_ids.split(",") if rid.strip()]

    result = await session.execute(
        select(PublishedPost).where(
            PublishedPost.generation_result_id.in_(ids),
            PublishedPost.client_id == client_id,
        )
    )
    posts = result.scalars().all()
    post_map = {str(p.generation_result_id): str(p.id) for p in posts}

    statuses = {str(rid): post_map.get(str(rid)) for rid in ids}
    return PublishStatusResponse(statuses=statuses)
