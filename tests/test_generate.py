import json
from datetime import date
from unittest.mock import AsyncMock, patch

import pytest

TODAY = date.today().isoformat()

MOCK_AI_RESPONSE = {
    "results": [
        {"channel_id": "blog", "text": "Blog post about today's thoughts."},
        {"channel_id": "twitter", "text": "Quick thought of the day!"},
    ]
}

MOCK_OPENAI_BODY = {
    "choices": [
        {
            "message": {
                "content": json.dumps(MOCK_AI_RESPONSE),
            }
        }
    ],
    "model": "gpt-5.2",
}


def _mock_openai(response_body=None):
    """Patch httpx.AsyncClient to return a mock OpenAI response."""
    body = response_body or MOCK_OPENAI_BODY
    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_resp.json = lambda: body
    mock_resp.raise_for_status = lambda: None

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    return patch("app.services.ai.httpx.AsyncClient", return_value=mock_client)


async def _create_text_item(http_client, headers, content="Test note", day=TODAY):
    resp = await http_client.post(
        "/api/v1/inputs",
        json={"type": "text", "content": content, "date": day},
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()


@pytest.mark.asyncio
async def test_generate_success(http_client, client_headers):
    await _create_text_item(http_client, client_headers)
    with _mock_openai():
        resp = await http_client.post(
            "/api/v1/generate",
            json={"date": TODAY, "channels": ["blog", "twitter"]},
            headers=client_headers,
        )
    assert resp.status_code == 201
    data = resp.json()
    assert data["date"] == TODAY
    assert len(data["results"]) == 2
    channels = {r["channel_id"] for r in data["results"]}
    assert channels == {"blog", "twitter"}
    assert data["results"][0]["text"]
    assert data["results"][0]["model"] == "gpt-5.2"


@pytest.mark.asyncio
async def test_generate_no_items(http_client, client_headers):
    resp = await http_client.post(
        "/api/v1/generate",
        json={"date": TODAY},
        headers=client_headers,
    )
    assert resp.status_code == 400
    assert "No input items" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_generate_unknown_channel(http_client, client_headers):
    await _create_text_item(http_client, client_headers)
    resp = await http_client.post(
        "/api/v1/generate",
        json={"date": TODAY, "channels": ["nonexistent"]},
        headers=client_headers,
    )
    assert resp.status_code == 400
    assert "Unknown channel" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_generate_default_channels(http_client, client_headers):
    """When no channels specified, uses all channels from config."""
    all_channels_response = {
        "results": [
            {"channel_id": "blog", "text": "Blog"},
            {"channel_id": "diary", "text": "Diary"},
            {"channel_id": "tg_personal", "text": "TG Personal"},
            {"channel_id": "tg_public", "text": "TG Public"},
            {"channel_id": "twitter", "text": "Tweet"},
        ]
    }
    body = {
        "choices": [{"message": {"content": json.dumps(all_channels_response)}}],
        "model": "gpt-5.2",
    }
    await _create_text_item(http_client, client_headers)
    with _mock_openai(response_body=body):
        resp = await http_client.post(
            "/api/v1/generate",
            json={"date": TODAY},
            headers=client_headers,
        )
    assert resp.status_code == 201
    assert len(resp.json()["results"]) == 5


@pytest.mark.asyncio
async def test_generate_with_style_override(http_client, client_headers):
    await _create_text_item(http_client, client_headers)
    with _mock_openai():
        resp = await http_client.post(
            "/api/v1/generate",
            json={
                "date": TODAY,
                "channels": ["blog", "twitter"],
                "style_override": "funny",
            },
            headers=client_headers,
        )
    assert resp.status_code == 201
    for r in resp.json()["results"]:
        assert r["style"] == "funny"


@pytest.mark.asyncio
async def test_generate_with_language_override(http_client, client_headers):
    await _create_text_item(http_client, client_headers)
    with _mock_openai():
        resp = await http_client.post(
            "/api/v1/generate",
            json={
                "date": TODAY,
                "channels": ["blog", "twitter"],
                "language_override": "en",
            },
            headers=client_headers,
        )
    assert resp.status_code == 201
    for r in resp.json()["results"]:
        assert r["language"] == "en"


@pytest.mark.asyncio
async def test_generate_invalid_json_retries(http_client, client_headers):
    """AI returns invalid JSON twice, then valid on third try."""
    call_count = 0

    def make_response():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            content = "not valid json at all"
        else:
            content = json.dumps(MOCK_AI_RESPONSE)
        return {
            "choices": [{"message": {"content": content}}],
            "model": "gpt-5.2",
        }

    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_resp.json = make_response
    mock_resp.raise_for_status = lambda: None

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    await _create_text_item(http_client, client_headers)
    with patch("app.services.ai.httpx.AsyncClient", return_value=mock_client):
        resp = await http_client.post(
            "/api/v1/generate",
            json={"date": TODAY, "channels": ["blog", "twitter"]},
            headers=client_headers,
        )
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_generate_saves_to_db(http_client, client_headers):
    """Generation results are persisted and visible in GET /days/{date}."""
    await _create_text_item(http_client, client_headers)
    with _mock_openai():
        await http_client.post(
            "/api/v1/generate",
            json={"date": TODAY, "channels": ["blog", "twitter"]},
            headers=client_headers,
        )
    day_resp = await http_client.get(
        f"/api/v1/days/{TODAY}", headers=client_headers
    )
    assert day_resp.status_code == 200
    data = day_resp.json()
    assert len(data["input_items"]) == 1
    assert len(data["generations"]) == 1
    assert len(data["generations"][0]["results"]) == 2


@pytest.mark.asyncio
async def test_get_day_empty(http_client, client_headers):
    resp = await http_client.get(
        "/api/v1/days/2020-01-01", headers=client_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["input_items"] == []
    assert data["generations"] == []


@pytest.mark.asyncio
async def test_multiple_generations_per_day(http_client, client_headers):
    await _create_text_item(http_client, client_headers, "Note 1")
    with _mock_openai():
        await http_client.post(
            "/api/v1/generate",
            json={"date": TODAY, "channels": ["blog", "twitter"]},
            headers=client_headers,
        )
    await _create_text_item(http_client, client_headers, "Note 2")
    with _mock_openai():
        await http_client.post(
            "/api/v1/generate",
            json={"date": TODAY, "channels": ["blog", "twitter"]},
            headers=client_headers,
        )
    day_resp = await http_client.get(
        f"/api/v1/days/{TODAY}", headers=client_headers
    )
    data = day_resp.json()
    assert len(data["input_items"]) == 2
    assert len(data["generations"]) == 2
