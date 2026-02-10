import uuid
import datetime as dt

from pydantic import BaseModel, Field


class GenerateRequest(BaseModel):
    date: dt.date = Field(default_factory=dt.date.today)
    channels: list[str] | None = None  # None = all active
    style_override: str | None = None
    language_override: str | None = None


class RegenerateRequest(BaseModel):
    channels: list[str] | None = None  # None = same channels as original


class GenerationResultResponse(BaseModel):
    id: uuid.UUID
    channel_id: str
    style: str
    language: str
    text: str
    model: str

    model_config = {"from_attributes": True}


class GenerationResponse(BaseModel):
    id: uuid.UUID
    date: dt.date
    results: list[GenerationResultResponse]
    created_at: dt.datetime

    model_config = {"from_attributes": True}
