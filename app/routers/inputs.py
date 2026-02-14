import uuid
import datetime as dt

from fastapi import APIRouter, Depends, Form, HTTPException, Query, UploadFile
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_session
from app.dependencies import get_client_id
from app.models.input_item import InputItem
from app.models.input_item_edit import InputItemEdit
from app.schemas.input_item import (
    InputItemCreateRequest,
    InputItemResponse,
    InputItemUpdateRequest,
    InputItemWithEditsResponse,
)
from app.services.file_storage import (
    ALLOWED_CONTENT_TYPES,
    MAX_IMAGE_SIZE,
    UPLOAD_DIR,
    get_upload_path,
    save_upload,
)
from app.services.url_extractor import extract_text_from_url

router = APIRouter(prefix="/inputs", tags=["inputs"])


@router.post("", response_model=InputItemResponse, status_code=201)
async def create_input_item(
    body: InputItemCreateRequest,
    client_id: uuid.UUID = Depends(get_client_id),
    session: AsyncSession = Depends(get_session),
):
    extracted_text = None
    extract_error = None
    if body.type == "url":
        extracted_text, extract_error = await extract_text_from_url(body.content)
    item = InputItem(
        client_id=client_id,
        date=body.date,
        type=body.type.value,
        content=body.content,
        extracted_text=extracted_text,
        extract_error=extract_error,
        importance=body.importance,
        include_in_generation=body.include_in_generation,
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item


@router.post("/upload", response_model=InputItemResponse, status_code=201)
async def upload_image(
    file: UploadFile,
    date: dt.date = Form(default_factory=dt.date.today),
    client_id: uuid.UUID = Depends(get_client_id),
    session: AsyncSession = Depends(get_session),
):
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}. Allowed: jpg, png, webp",
        )
    data = await file.read()
    if len(data) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=413, detail="Image exceeds 5 MB limit")
    ext = ALLOWED_CONTENT_TYPES[file.content_type]
    path = get_upload_path(client_id, date, ext)
    await save_upload(data, path)
    relative_path = str(path.relative_to(UPLOAD_DIR))
    item = InputItem(
        client_id=client_id,
        date=date,
        type="image",
        content=relative_path,
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item


@router.get("", response_model=list[InputItemWithEditsResponse])
async def list_input_items(
    date: dt.date = Query(...),
    client_id: uuid.UUID = Depends(get_client_id),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(InputItem)
        .where(
            InputItem.client_id == client_id,
            InputItem.date == date,
            InputItem.cleared == False,
        )
        .options(selectinload(InputItem.edits))
        .order_by(InputItem.created_at)
    )
    return result.scalars().all()


@router.get("/{item_id}", response_model=InputItemWithEditsResponse)
async def get_input_item(
    item_id: uuid.UUID,
    client_id: uuid.UUID = Depends(get_client_id),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(InputItem)
        .where(InputItem.id == item_id, InputItem.client_id == client_id)
        .options(selectinload(InputItem.edits))
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@router.put("/{item_id}", response_model=InputItemWithEditsResponse)
async def update_input_item(
    item_id: uuid.UUID,
    body: InputItemUpdateRequest,
    client_id: uuid.UUID = Depends(get_client_id),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(InputItem).where(
            InputItem.id == item_id, InputItem.client_id == client_id
        )
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    # Save old content to edit history if content changed
    if body.content is not None and body.content != item.content:
        edit = InputItemEdit(
            item_id=item.id,
            old_content=item.content,
        )
        session.add(edit)
        item.content = body.content
    if body.importance is not None:
        item.importance = body.importance
    if body.include_in_generation is not None:
        item.include_in_generation = body.include_in_generation
    await session.commit()
    # Re-query with selectinload to get fresh edits
    result = await session.execute(
        select(InputItem)
        .where(InputItem.id == item_id)
        .options(selectinload(InputItem.edits))
    )
    item = result.scalar_one()
    return item


@router.delete("/{item_id}", status_code=204)
async def delete_input_item(
    item_id: uuid.UUID,
    client_id: uuid.UUID = Depends(get_client_id),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(InputItem).where(
            InputItem.id == item_id, InputItem.client_id == client_id
        )
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    # Soft-delete: mark as cleared instead of removing from DB
    item.cleared = True
    await session.commit()


@router.get("/export")
async def export_day(
    date: dt.date = Query(...),
    format: str = Query(default="plain"),
    client_id: uuid.UUID = Depends(get_client_id),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(InputItem)
        .where(
            InputItem.client_id == client_id,
            InputItem.date == date,
            InputItem.cleared == False,
        )
        .order_by(InputItem.created_at)
    )
    items = result.scalars().all()
    lines = []
    for item in items:
        time_str = item.created_at.strftime("%H:%M")
        if item.type == "text":
            lines.append(f"[{time_str}] {item.content}")
        elif item.type == "url":
            lines.append(f"[{time_str}] {item.content}")
            if item.extracted_text:
                lines.append(f"  > {item.extracted_text[:200]}")
        elif item.type == "image":
            lines.append(f"[{time_str}] [Image]")
    return {"text": "\n".join(lines), "date": str(date), "count": len(items)}


@router.delete("", status_code=204)
async def clear_day(
    date: dt.date = Query(...),
    client_id: uuid.UUID = Depends(get_client_id),
    session: AsyncSession = Depends(get_session),
):
    await session.execute(
        update(InputItem)
        .where(
            InputItem.client_id == client_id,
            InputItem.date == date,
            InputItem.cleared == False,
        )
        .values(cleared=True)
    )
    await session.commit()
