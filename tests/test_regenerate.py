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

MOCK_REGEN_RESPONSE = {
    "results": [
        {"channel_id": "blog", "text": "A completely different blog post."},
        {"channel_id": "twitter", "text": "Another take on the day!"},
    ]
}


def _mock_openai(response_body=None):
    body = response_body or {
        "choices": [{"message": {"content": json.dumps(MOCK_AI_RESPONSE)}}],
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


def _mock_regen():
    body = {
        "choices": [{"message": {"content": json.dumps(MOCK_REGEN_RESPONSE)}}],
        "model": "gpt-5.2",
    }
    return _mock_openai(body)


async def _create_and_generate(http_client, headers):
    await http_client.post(
        "/api/v1/inputs",
        json={"type": "text", "content": "Test note", "date": TODAY},
        headers=headers,
    )
    with _mock_openai():
        resp = await http_client.post(
            "/api/v1/generate",
            json={"date": TODAY, "channels": ["blog", "twitter"]},
            headers=headers,
        )
    return resp.json()


@pytest.mark.asyncio
async def test_regenerate_success(http_client, client_headers):
    gen = await _create_and_generate(http_client, client_headers)
    gen_id = gen["id"]
    with _mock_regen():
        resp = await http_client.post(
            f"/api/v1/generate/{gen_id}/regenerate",
            json={},
            headers=client_headers,
        )
    assert resp.status_code == 201
    data = resp.json()
    assert data["id"] != gen_id
    assert len(data["results"]) == 2
    assert data["results"][0]["text"] == "A completely different blog post."


@pytest.mark.asyncio
async def test_regenerate_specific_channels(http_client, client_headers):
    gen = await _create_and_generate(http_client, client_headers)
    gen_id = gen["id"]
    regen_body = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {"results": [{"channel_id": "blog", "text": "Blog only regen"}]}
                    )
                }
            }
        ],
        "model": "gpt-5.2",
    }
    with _mock_openai(regen_body):
        resp = await http_client.post(
            f"/api/v1/generate/{gen_id}/regenerate",
            json={"channels": ["blog"]},
            headers=client_headers,
        )
    assert resp.status_code == 201
    assert len(resp.json()["results"]) == 1
    assert resp.json()["results"][0]["channel_id"] == "blog"


@pytest.mark.asyncio
async def test_regenerate_not_found(http_client, client_headers):
    resp = await http_client.post(
        "/api/v1/generate/00000000-0000-0000-0000-000000000000/regenerate",
        json={},
        headers=client_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_regenerate_appears_in_day(http_client, client_headers):
    gen = await _create_and_generate(http_client, client_headers)
    gen_id = gen["id"]
    with _mock_regen():
        await http_client.post(
            f"/api/v1/generate/{gen_id}/regenerate",
            json={},
            headers=client_headers,
        )
    day_resp = await http_client.get(
        f"/api/v1/days/{TODAY}", headers=client_headers
    )
    data = day_resp.json()
    assert len(data["generations"]) == 2
