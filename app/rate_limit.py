import time
import uuid
from collections import defaultdict
from datetime import date

from fastapi import Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies import get_client_id
from app.models.generation import Generation
from app.services.product_config import get_product_config

# In-memory store for API rate limiting: {client_id: [timestamp, ...]}
_request_log: dict[str, list[float]] = defaultdict(list)


async def check_api_rate_limit(
    client_id: uuid.UUID = Depends(get_client_id),
) -> None:
    """Check API requests per minute rate limit."""
    config = get_product_config()
    limit = config["rate_limits"]["api_requests_per_minute"]

    key = str(client_id)
    now = time.monotonic()
    cutoff = now - 60

    # Clean old entries
    _request_log[key] = [t for t in _request_log[key] if t > cutoff]

    if len(_request_log[key]) >= limit:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    _request_log[key].append(now)


async def check_generation_rate_limit(
    client_id: uuid.UUID = Depends(get_client_id),
    session: AsyncSession = Depends(get_session),
) -> None:
    """Check AI generations per day rate limit."""
    config = get_product_config()
    limit = config["rate_limits"]["ai_generations_per_day"]

    result = await session.execute(
        select(func.count(Generation.id)).where(
            Generation.client_id == client_id,
            Generation.date == date.today(),
        )
    )
    count = result.scalar_one()

    if count >= limit:
        raise HTTPException(
            status_code=429,
            detail=f"Generation limit exceeded ({limit}/day)",
        )
