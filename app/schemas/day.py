import datetime as dt

from pydantic import BaseModel

from app.schemas.generation import GenerationResponse
from app.schemas.input_item import InputItemWithEditsResponse


class DayResponse(BaseModel):
    date: dt.date
    input_items: list[InputItemWithEditsResponse]
    generations: list[GenerationResponse]


class DaySummary(BaseModel):
    date: dt.date
    input_count: int
    generation_count: int


class DayListResponse(BaseModel):
    items: list[DaySummary]
    cursor: str | None = None
