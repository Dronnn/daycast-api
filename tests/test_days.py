import json
from datetime import date
from unittest.mock import AsyncMock, patch

import pytest

TODAY = date.today().isoformat()


def _mock_openai():
    body = {
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
    mock_resp.json = lambda: body
    mock_resp.raise_for_status = lambda: None

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    return patch("app.services.ai.httpx.AsyncClient", return_value=mock_client)


async def _add_item(http_client, headers, content="Note", day=TODAY):
    await http_client.post(
        "/api/v1/inputs",
        json={"type": "text", "content": content, "date": day},
        headers=headers,
    )


@pytest.mark.asyncio
async def test_list_days(http_client, client_headers):
    await _add_item(http_client, client_headers, day="2024-01-01")
    await _add_item(http_client, client_headers, day="2024-01-02")
    await _add_item(http_client, client_headers, day="2024-01-02")

    resp = await http_client.get("/api/v1/days", headers=client_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 2
    # Sorted desc
    assert data["items"][0]["date"] == "2024-01-02"
    assert data["items"][0]["input_count"] == 2
    assert data["items"][1]["date"] == "2024-01-01"
    assert data["items"][1]["input_count"] == 1


@pytest.mark.asyncio
async def test_list_days_with_generation_count(http_client, client_headers):
    await _add_item(http_client, client_headers, day=TODAY)
    with _mock_openai():
        await http_client.post(
            "/api/v1/generate",
            json={"date": TODAY, "channels": ["blog"]},
            headers=client_headers,
        )
    resp = await http_client.get("/api/v1/days", headers=client_headers)
    items = resp.json()["items"]
    assert items[0]["generation_count"] == 1


@pytest.mark.asyncio
async def test_list_days_cursor_pagination(http_client, client_headers):
    for i in range(5):
        await _add_item(http_client, client_headers, day=f"2024-03-{10+i:02d}")

    resp = await http_client.get(
        "/api/v1/days?limit=2", headers=client_headers
    )
    data = resp.json()
    assert len(data["items"]) == 2
    assert data["cursor"] is not None

    resp2 = await http_client.get(
        f"/api/v1/days?limit=2&cursor={data['cursor']}", headers=client_headers
    )
    data2 = resp2.json()
    assert len(data2["items"]) == 2
    assert data2["items"][0]["date"] < data["items"][-1]["date"]


@pytest.mark.asyncio
async def test_list_days_search(http_client, client_headers):
    await _add_item(http_client, client_headers, content="Python tutorial", day="2024-04-01")
    await _add_item(http_client, client_headers, content="Cooking recipe", day="2024-04-02")

    resp = await http_client.get(
        "/api/v1/days?search=Python", headers=client_headers
    )
    data = resp.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["date"] == "2024-04-01"


@pytest.mark.asyncio
async def test_list_days_empty(http_client, client_headers):
    resp = await http_client.get("/api/v1/days", headers=client_headers)
    assert resp.status_code == 200
    assert resp.json()["items"] == []


@pytest.mark.asyncio
async def test_delete_day(http_client, client_headers):
    await _add_item(http_client, client_headers, day="2024-05-01")
    await _add_item(http_client, client_headers, day="2024-05-01")
    with _mock_openai():
        await http_client.post(
            "/api/v1/generate",
            json={"date": "2024-05-01", "channels": ["blog"]},
            headers=client_headers,
        )

    resp = await http_client.delete(
        "/api/v1/days/2024-05-01", headers=client_headers
    )
    assert resp.status_code == 204

    day_resp = await http_client.get(
        "/api/v1/days/2024-05-01", headers=client_headers
    )
    data = day_resp.json()
    assert data["input_items"] == []
    assert data["generations"] == []


@pytest.mark.asyncio
async def test_delete_day_does_not_affect_other_days(http_client, client_headers):
    await _add_item(http_client, client_headers, day="2024-06-01")
    await _add_item(http_client, client_headers, day="2024-06-02")

    await http_client.delete("/api/v1/days/2024-06-01", headers=client_headers)

    resp = await http_client.get(
        "/api/v1/days/2024-06-02", headers=client_headers
    )
    assert len(resp.json()["input_items"]) == 1
