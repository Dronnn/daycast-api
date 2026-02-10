from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.services.file_storage import UPLOAD_DIR

router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.get("/{file_path:path}")
async def serve_upload(file_path: str):
    full_path = (UPLOAD_DIR / file_path).resolve()
    if not full_path.is_relative_to(UPLOAD_DIR.resolve()):
        raise HTTPException(status_code=403, detail="Forbidden")
    if not full_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(full_path)
