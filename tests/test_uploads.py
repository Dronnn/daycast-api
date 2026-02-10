import io
import shutil
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest

from app.services.file_storage import UPLOAD_DIR

TODAY = date.today().isoformat()

TINY_JPEG = (
    b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    b"\xff\xd9"
)

TINY_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx"
    b"\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
)


@pytest.fixture(autouse=True)
def cleanup_uploads():
    yield
    if UPLOAD_DIR.exists():
        shutil.rmtree(UPLOAD_DIR)


@pytest.mark.asyncio
async def test_upload_jpeg(http_client, client_headers):
    resp = await http_client.post(
        "/api/v1/inputs/upload",
        headers=client_headers,
        files={"file": ("photo.jpg", io.BytesIO(TINY_JPEG), "image/jpeg")},
        data={"date": TODAY},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["type"] == "image"
    assert data["content"].endswith(".jpg")
    # content is relative to UPLOAD_DIR: {client_id}/{date}/{uuid}.jpg
    assert "/" in data["content"]


@pytest.mark.asyncio
async def test_upload_png(http_client, client_headers):
    resp = await http_client.post(
        "/api/v1/inputs/upload",
        headers=client_headers,
        files={"file": ("photo.png", io.BytesIO(TINY_PNG), "image/png")},
        data={"date": TODAY},
    )
    assert resp.status_code == 201
    assert resp.json()["content"].endswith(".png")


@pytest.mark.asyncio
async def test_upload_default_date(http_client, client_headers):
    resp = await http_client.post(
        "/api/v1/inputs/upload",
        headers=client_headers,
        files={"file": ("photo.jpg", io.BytesIO(TINY_JPEG), "image/jpeg")},
    )
    assert resp.status_code == 201
    assert resp.json()["date"] == TODAY


@pytest.mark.asyncio
async def test_upload_unsupported_type(http_client, client_headers):
    resp = await http_client.post(
        "/api/v1/inputs/upload",
        headers=client_headers,
        files={"file": ("doc.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")},
        data={"date": TODAY},
    )
    assert resp.status_code == 400
    assert "Unsupported" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_upload_too_large(http_client, client_headers):
    big_data = b"\xff" * (5 * 1024 * 1024 + 1)
    resp = await http_client.post(
        "/api/v1/inputs/upload",
        headers=client_headers,
        files={"file": ("big.jpg", io.BytesIO(big_data), "image/jpeg")},
        data={"date": TODAY},
    )
    assert resp.status_code == 413


@pytest.mark.asyncio
async def test_upload_and_serve(http_client, client_headers):
    upload_resp = await http_client.post(
        "/api/v1/inputs/upload",
        headers=client_headers,
        files={"file": ("photo.jpg", io.BytesIO(TINY_JPEG), "image/jpeg")},
        data={"date": TODAY},
    )
    assert upload_resp.status_code == 201
    stored_path = upload_resp.json()["content"]
    # content is already relative to UPLOAD_DIR
    serve_resp = await http_client.get(f"/api/v1/uploads/{stored_path}")
    assert serve_resp.status_code == 200
    assert serve_resp.content == TINY_JPEG


@pytest.mark.asyncio
async def test_serve_not_found(http_client):
    resp = await http_client.get("/api/v1/uploads/nonexistent/file.jpg")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_serve_path_traversal(http_client):
    resp = await http_client.get("/api/v1/uploads/../../etc/passwd")
    assert resp.status_code in (403, 404)


@pytest.mark.asyncio
async def test_upload_appears_in_list(http_client, client_headers):
    await http_client.post(
        "/api/v1/inputs/upload",
        headers=client_headers,
        files={"file": ("photo.jpg", io.BytesIO(TINY_JPEG), "image/jpeg")},
        data={"date": TODAY},
    )
    list_resp = await http_client.get(
        f"/api/v1/inputs?date={TODAY}", headers=client_headers
    )
    items = list_resp.json()
    assert len(items) == 1
    assert items[0]["type"] == "image"
