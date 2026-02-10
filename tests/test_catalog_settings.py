import pytest


@pytest.mark.asyncio
async def test_list_channels(http_client):
    resp = await http_client.get("/api/v1/channels")
    assert resp.status_code == 200
    data = resp.json()
    assert "blog" in data
    assert "twitter" in data
    assert data["blog"]["max_length"] == 3000


@pytest.mark.asyncio
async def test_list_styles(http_client):
    resp = await http_client.get("/api/v1/styles")
    assert resp.status_code == 200
    data = resp.json()
    assert "casual" in data
    assert "funny" in data


@pytest.mark.asyncio
async def test_list_languages(http_client):
    resp = await http_client.get("/api/v1/languages")
    assert resp.status_code == 200
    data = resp.json()
    assert "ru" in data
    assert data["ru"]["name"] == "Russian"


@pytest.mark.asyncio
async def test_save_and_get_channel_settings(http_client, client_headers):
    body = {
        "channels": [
            {
                "channel_id": "blog",
                "is_active": True,
                "default_style": "detailed",
                "default_language": "en",
            },
            {
                "channel_id": "twitter",
                "is_active": False,
                "default_style": "concise",
                "default_language": "ru",
            },
        ]
    }
    resp = await http_client.post(
        "/api/v1/settings/channels", json=body, headers=client_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    by_ch = {s["channel_id"]: s for s in data}
    assert by_ch["blog"]["default_style"] == "detailed"
    assert by_ch["twitter"]["is_active"] is False

    # GET
    get_resp = await http_client.get(
        "/api/v1/settings/channels", headers=client_headers
    )
    assert get_resp.status_code == 200
    assert len(get_resp.json()) == 2


@pytest.mark.asyncio
async def test_update_existing_channel_settings(http_client, client_headers):
    body1 = {
        "channels": [
            {"channel_id": "blog", "is_active": True, "default_style": "casual", "default_language": "ru"}
        ]
    }
    await http_client.post(
        "/api/v1/settings/channels", json=body1, headers=client_headers
    )

    body2 = {
        "channels": [
            {"channel_id": "blog", "is_active": False, "default_style": "funny", "default_language": "en"}
        ]
    }
    resp = await http_client.post(
        "/api/v1/settings/channels", json=body2, headers=client_headers
    )
    data = resp.json()
    by_ch = {s["channel_id"]: s for s in data}
    assert by_ch["blog"]["is_active"] is False
    assert by_ch["blog"]["default_style"] == "funny"


@pytest.mark.asyncio
async def test_get_settings_empty(http_client, client_headers):
    resp = await http_client.get(
        "/api/v1/settings/channels", headers=client_headers
    )
    assert resp.status_code == 200
    assert resp.json() == []
