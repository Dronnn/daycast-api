import uuid
from datetime import date
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
UPLOAD_DIR = _PROJECT_ROOT / "data" / "uploads"
ALLOWED_CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5 MB


def get_upload_path(client_id: uuid.UUID, day: date, file_ext: str) -> Path:
    file_id = uuid.uuid4()
    return UPLOAD_DIR / str(client_id) / day.isoformat() / f"{file_id}{file_ext}"


async def save_upload(data: bytes, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
