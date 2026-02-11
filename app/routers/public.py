import datetime as dt
from xml.sax.saxutils import escape as xml_escape

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import Date, cast, distinct, extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.generation import Generation
from app.models.generation_result import GenerationResult
from app.models.input_item import InputItem
from app.models.published_post import PublishedPost
from app.schemas.publish import (
    ArchiveMonth,
    ArchiveResponse,
    CalendarDate,
    CalendarResponse,
    PublishedPostListResponse,
    PublishedPostResponse,
    StatsResponse,
)

router = APIRouter(prefix="/public", tags=["public"])


async def _build_post_response(
    post: PublishedPost,
    result: GenerationResult | None,
    generation: Generation | None,
    session: AsyncSession,
) -> PublishedPostResponse:
    # Input-based post
    if post.input_item_id and result is None:
        return PublishedPostResponse(
            id=post.id,
            slug=post.slug,
            channel_id=None,
            style=None,
            language=None,
            text=post.text or "",
            date=post.published_at.date(),
            published_at=post.published_at,
            input_items_preview=[],
            source="input",
        )

    # Generation-based post
    preview = []
    if generation:
        items_result = await session.execute(
            select(InputItem)
            .where(
                InputItem.client_id == generation.client_id,
                InputItem.date == generation.date,
                InputItem.cleared == False,
            )
            .order_by(InputItem.created_at)
            .limit(5)
        )
        items = items_result.scalars().all()
        preview = [item.content[:80] for item in items]

    return PublishedPostResponse(
        id=post.id,
        slug=post.slug,
        channel_id=result.channel_id if result else None,
        style=result.style if result else None,
        language=result.language if result else None,
        text=result.text if result else (post.text or ""),
        date=generation.date if generation else post.published_at.date(),
        published_at=post.published_at,
        input_items_preview=preview,
        source="generation" if result else "input",
    )


@router.get("/posts", response_model=PublishedPostListResponse)
async def list_posts(
    limit: int = Query(default=10, ge=1, le=50),
    cursor: str | None = None,
    channel: str | None = None,
    language: str | None = None,
    date: str | None = None,
    session: AsyncSession = Depends(get_session),
):
    query = (
        select(PublishedPost, GenerationResult, Generation)
        .outerjoin(GenerationResult, PublishedPost.generation_result_id == GenerationResult.id)
        .outerjoin(Generation, GenerationResult.generation_id == Generation.id)
    )

    if cursor:
        cursor_dt = dt.datetime.fromisoformat(cursor)
        query = query.where(PublishedPost.published_at < cursor_dt)

    if channel:
        query = query.where(GenerationResult.channel_id == channel)

    if language:
        query = query.where(GenerationResult.language == language)

    if date:
        query = query.where(Generation.date == dt.date.fromisoformat(date))

    query = query.order_by(PublishedPost.published_at.desc()).limit(limit + 1)

    result = await session.execute(query)
    rows = result.all()

    has_more = len(rows) > limit
    rows = rows[:limit]

    items = []
    for post, gen_result, generation in rows:
        resp = await _build_post_response(post, gen_result, generation, session)
        items.append(resp)

    next_cursor = None
    if has_more and items:
        next_cursor = items[-1].published_at.isoformat()

    return PublishedPostListResponse(items=items, cursor=next_cursor, has_more=has_more)


@router.get("/posts/{slug}", response_model=PublishedPostResponse)
async def get_post(
    slug: str,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(PublishedPost, GenerationResult, Generation)
        .outerjoin(GenerationResult, PublishedPost.generation_result_id == GenerationResult.id)
        .outerjoin(Generation, GenerationResult.generation_id == Generation.id)
        .where(PublishedPost.slug == slug)
    )
    row = result.one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Post not found")

    post, gen_result, generation = row
    return await _build_post_response(post, gen_result, generation, session)


@router.get("/calendar", response_model=CalendarResponse)
async def get_calendar(
    year: int,
    month: int,
    session: AsyncSession = Depends(get_session),
):
    start = dt.date(year, month, 1)
    if month == 12:
        end = dt.date(year + 1, 1, 1)
    else:
        end = dt.date(year, month + 1, 1)

    result = await session.execute(
        select(Generation.date, func.count(PublishedPost.id))
        .join(GenerationResult, PublishedPost.generation_result_id == GenerationResult.id)
        .join(Generation, GenerationResult.generation_id == Generation.id)
        .where(Generation.date >= start, Generation.date < end)
        .group_by(Generation.date)
        .order_by(Generation.date)
    )
    rows = result.all()

    dates = [CalendarDate(date=row[0], post_count=row[1]) for row in rows]
    return CalendarResponse(dates=dates)


@router.get("/archive", response_model=ArchiveResponse)
async def get_archive(
    session: AsyncSession = Depends(get_session),
):
    month_key = func.to_char(Generation.date, "YYYY-MM")
    result = await session.execute(
        select(
            month_key.label("month_key"),
            func.count(PublishedPost.id).label("cnt"),
        )
        .select_from(PublishedPost)
        .join(GenerationResult, PublishedPost.generation_result_id == GenerationResult.id)
        .join(Generation, GenerationResult.generation_id == Generation.id)
        .group_by(month_key)
        .order_by(month_key.desc())
    )
    rows = result.all()

    import calendar as cal
    months = []
    for row in rows:
        year, mon = row[0].split("-")
        label = f"{cal.month_name[int(mon)]} {year}"
        months.append(ArchiveMonth(month=row[0], label=label, post_count=row[1]))
    return ArchiveResponse(months=months)


@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    session: AsyncSession = Depends(get_session),
):
    total = await session.execute(
        select(func.count(PublishedPost.id))
    )
    total_posts = total.scalar() or 0

    days_result = await session.execute(
        select(func.count(distinct(Generation.date)))
        .select_from(PublishedPost)
        .join(GenerationResult, PublishedPost.generation_result_id == GenerationResult.id)
        .join(Generation, GenerationResult.generation_id == Generation.id)
    )
    total_days = days_result.scalar() or 0

    channels_result = await session.execute(
        select(distinct(GenerationResult.channel_id))
        .join(PublishedPost, PublishedPost.generation_result_id == GenerationResult.id)
    )
    channels_used = [row[0] for row in channels_result.all()]

    return StatsResponse(
        total_posts=total_posts,
        total_days=total_days,
        channels_used=channels_used,
    )


@router.get("/rss")
async def rss_feed(
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(PublishedPost, GenerationResult, Generation)
        .outerjoin(GenerationResult, PublishedPost.generation_result_id == GenerationResult.id)
        .outerjoin(Generation, GenerationResult.generation_id == Generation.id)
        .order_by(PublishedPost.published_at.desc())
        .limit(50)
    )
    rows = result.all()

    items_xml = []
    for post, gen_result, generation in rows:
        pub_date = post.published_at.strftime("%a, %d %b %Y %H:%M:%S +0000")
        title = gen_result.channel_id if gen_result else "Personal"
        post_date = str(generation.date) if generation else str(post.published_at.date())
        text = gen_result.text if gen_result else (post.text or "")
        items_xml.append(
            f"""    <item>
      <title>{xml_escape(title)} - {xml_escape(post_date)}</title>
      <link>http://192.168.31.131:3000/post/{xml_escape(post.slug)}</link>
      <guid isPermaLink="false">{post.id}</guid>
      <pubDate>{pub_date}</pubDate>
      <description>{xml_escape(text[:500])}</description>
    </item>"""
        )

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>DayCast Blog</title>
    <link>http://192.168.31.131:3000</link>
    <description>AI-generated content from daily thoughts</description>
    <language>en</language>
    <lastBuildDate>{dt.datetime.now(dt.timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")}</lastBuildDate>
{chr(10).join(items_xml)}
  </channel>
</rss>"""

    return Response(content=xml, media_type="application/rss+xml")
