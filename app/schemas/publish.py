import uuid
import datetime as dt

from pydantic import BaseModel


class PublishRequest(BaseModel):
    generation_result_id: uuid.UUID


class PublishInputRequest(BaseModel):
    input_item_id: uuid.UUID


class PublishedPostResponse(BaseModel):
    id: uuid.UUID
    slug: str
    channel_id: str | None = None
    style: str | None = None
    language: str | None = None
    text: str
    date: dt.date
    published_at: dt.datetime
    input_items_preview: list[str] = []
    source: str = "generation"  # "generation" or "input"

    model_config = {"from_attributes": True}


class PublishStatusResponse(BaseModel):
    statuses: dict[str, str | None]


class PublishedPostListResponse(BaseModel):
    items: list[PublishedPostResponse]
    cursor: str | None
    has_more: bool


class CalendarDate(BaseModel):
    date: dt.date
    post_count: int


class CalendarResponse(BaseModel):
    dates: list[CalendarDate]


class ArchiveMonth(BaseModel):
    month: str
    label: str
    post_count: int


class ArchiveResponse(BaseModel):
    months: list[ArchiveMonth]


class StatsResponse(BaseModel):
    total_posts: int
    total_days: int
    channels_used: list[str]
