import json
from datetime import date
from unittest.mock import AsyncMock, patch

import pytest

TODAY = date.today().isoformat()


@pytest.mark.asyncio
async def test_error_format_404(http_client, client_headers):
    resp = await http_client.get(
        "/api/v1/inputs/00000000-0000-0000-0000-000000000000",
        headers=client_headers,
    )
    assert resp.status_code == 404
    data = resp.json()
    assert "code" in data
    assert data["code"] == "not_found"
    assert "error" in data


@pytest.mark.asyncio
async def test_error_format_422(http_client, client_headers):
    resp = await http_client.post(
        "/api/v1/inputs",
        json={"type": "invalid_type", "content": "x"},
        headers=client_headers,
    )
    assert resp.status_code == 422
    data = resp.json()
    assert data["code"] == "validation_error"


@pytest.mark.asyncio
async def test_generation_rate_limit(http_client, client_headers):
    """Generation should be limited to N per day (default 10 in config)."""
    # Create an item
    await http_client.post(
        "/api/v1/inputs",
        json={"type": "text", "content": "test", "date": TODAY},
        headers=client_headers,
    )

    mock_body = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {"results": [{"channel_id": "blog", "text": "Blog"}]}
                    )
                }
            }
        ],
        "model": "gpt-5.2",
    }
    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_resp.json = lambda: mock_body
    mock_resp.raise_for_status = lambda: None
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.ai.httpx.AsyncClient", return_value=mock_client):
        # Generate 10 times (limit)
        for i in range(10):
            resp = await http_client.post(
                "/api/v1/generate",
                json={"date": TODAY, "channels": ["blog"]},
                headers=client_headers,
            )
            assert resp.status_code == 201, f"Failed on generation {i+1}: {resp.text}"

        # 11th should be rate limited
        resp = await http_client.post(
            "/api/v1/generate",
            json={"date": TODAY, "channels": ["blog"]},
            headers=client_headers,
        )
        assert resp.status_code == 429
        assert "limit" in resp.json()["error"].lower()
