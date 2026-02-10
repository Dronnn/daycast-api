import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_session
from app.dependencies import get_client_id
from app.models.generation import Generation
from app.models.input_item import InputItem
from app.schemas.day import DayListResponse, DayResponse, DaySummary

router = APIRouter(prefix="/days", tags=["days"])


@router.get("", response_model=DayListResponse)
async def list_days(
    client_id: uuid.UUID = Depends(get_client_id),
    session: AsyncSession = Depends(get_session),
    limit: int = Query(default=30, ge=1, le=100),
    cursor: str | None = Query(default=None),
    search: str | None = Query(default=None),
):
    # Subquery: distinct dates from input_items
    items_q = (
        select(
            InputItem.date,
            func.count(InputItem.id).label("input_count"),
        )
        .where(InputItem.client_id == client_id)
        .group_by(InputItem.date)
    )
    if search:
        items_q = items_q.where(InputItem.content.ilike(f"%{search}%"))

    items_sub = items_q.subquery()

    # Subquery: generation counts per date
    gen_sub = (
        select(
            Generation.date,
            func.count(Generation.id).label("generation_count"),
        )
        .where(Generation.client_id == client_id)
        .group_by(Generation.date)
        .subquery()
    )

    # Join
    query = (
        select(
            items_sub.c.date,
            items_sub.c.input_count,
            func.coalesce(gen_sub.c.generation_count, 0).label("generation_count"),
        )
        .outerjoin(gen_sub, items_sub.c.date == gen_sub.c.date)
        .order_by(items_sub.c.date.desc())
    )

    if cursor:
        query = query.where(items_sub.c.date < cursor)

    query = query.limit(limit + 1)  # fetch one extra for cursor

    result = await session.execute(query)
    rows = result.all()

    has_more = len(rows) > limit
    rows = rows[:limit]

    summaries = [
        DaySummary(
            date=row.date,
            input_count=row.input_count,
            generation_count=row.generation_count,
        )
        for row in rows
    ]
    next_cursor = str(rows[-1].date) if has_more and rows else None

    return DayListResponse(items=summaries, cursor=next_cursor)


@router.get("/{day}", response_model=DayResponse)
async def get_day(
    day: date,
    client_id: uuid.UUID = Depends(get_client_id),
    session: AsyncSession = Depends(get_session),
):
    # Load all items (including cleared) with their edit history
    items_result = await session.execute(
        select(InputItem)
        .where(InputItem.client_id == client_id, InputItem.date == day)
        .options(selectinload(InputItem.edits))
        .order_by(InputItem.created_at)
    )
    input_items = items_result.scalars().all()

    gen_result = await session.execute(
        select(Generation)
        .where(Generation.client_id == client_id, Generation.date == day)
        .options(selectinload(Generation.results))
        .order_by(Generation.created_at)
    )
    generations = gen_result.scalars().all()

    return DayResponse(
        date=day,
        input_items=input_items,
        generations=generations,
    )


@router.delete("/{day}", status_code=204)
async def delete_day(
    day: date,
    client_id: uuid.UUID = Depends(get_client_id),
    session: AsyncSession = Depends(get_session),
):
    # Delete generations (results cascade via FK)
    await session.execute(
        delete(Generation).where(
            Generation.client_id == client_id, Generation.date == day
        )
    )
    # Delete input items (edits cascade via FK)
    await session.execute(
        delete(InputItem).where(
            InputItem.client_id == client_id, InputItem.date == day
        )
    )
    await session.commit()
