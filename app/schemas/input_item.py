import uuid
import datetime as dt
from enum import Enum

from pydantic import BaseModel, Field


class InputItemType(str, Enum):
    text = "text"
    url = "url"
    image = "image"


class InputItemCreateRequest(BaseModel):
    type: InputItemType
    content: str = Field(max_length=4000)
    date: dt.date = Field(default_factory=dt.date.today)
    importance: int | None = Field(default=None, ge=1, le=5)
    include_in_generation: bool = True


class InputItemUpdateRequest(BaseModel):
    content: str | None = Field(default=None, max_length=4000)
    importance: int | None = Field(default=None, ge=1, le=5)
    include_in_generation: bool | None = None


class InputItemResponse(BaseModel):
    id: uuid.UUID
    type: InputItemType
    content: str
    extracted_text: str | None = None
    extract_error: str | None = None
    date: dt.date
    cleared: bool = False
    importance: int | None = None
    include_in_generation: bool = True
    created_at: dt.datetime
    updated_at: dt.datetime

    model_config = {"from_attributes": True}


class InputItemEditResponse(BaseModel):
    id: uuid.UUID
    old_content: str
    edited_at: dt.datetime

    model_config = {"from_attributes": True}


class InputItemWithEditsResponse(InputItemResponse):
    edits: list[InputItemEditResponse] = []
