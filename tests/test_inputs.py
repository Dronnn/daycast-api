import uuid
from datetime import date

import pytest

TODAY = date.today().isoformat()


@pytest.mark.asyncio
async def test_create_text_item(http_client, client_headers):
    resp = await http_client.post(
        "/api/v1/inputs",
        json={"type": "text", "content": "Hello world", "date": TODAY},
        headers=client_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["type"] == "text"
    assert data["content"] == "Hello world"
    assert data["date"] == TODAY


@pytest.mark.asyncio
async def test_create_url_item(http_client, client_headers):
    resp = await http_client.post(
        "/api/v1/inputs",
        json={"type": "url", "content": "https://example.com", "date": TODAY},
        headers=client_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["type"] == "url"


@pytest.mark.asyncio
async def test_create_image_item(http_client, client_headers):
    resp = await http_client.post(
        "/api/v1/inputs",
        json={"type": "image", "content": "base64data==", "date": TODAY},
        headers=client_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["type"] == "image"


@pytest.mark.asyncio
async def test_create_item_default_date(http_client, client_headers):
    resp = await http_client.post(
        "/api/v1/inputs",
        json={"type": "text", "content": "no date"},
        headers=client_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["date"] == TODAY


@pytest.mark.asyncio
async def test_create_item_invalid_type(http_client, client_headers):
    resp = await http_client.post(
        "/api/v1/inputs",
        json={"type": "video", "content": "bad"},
        headers=client_headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_item_missing_header(http_client):
    resp = await http_client.post(
        "/api/v1/inputs",
        json={"type": "text", "content": "no header"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_items_by_date(http_client, client_headers):
    await http_client.post(
        "/api/v1/inputs",
        json={"type": "text", "content": "item 1", "date": TODAY},
        headers=client_headers,
    )
    await http_client.post(
        "/api/v1/inputs",
        json={"type": "text", "content": "item 2", "date": TODAY},
        headers=client_headers,
    )
    resp = await http_client.get(
        f"/api/v1/inputs?date={TODAY}", headers=client_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["content"] == "item 1"
    assert data[1]["content"] == "item 2"


@pytest.mark.asyncio
async def test_list_items_empty(http_client, client_headers):
    resp = await http_client.get(
        "/api/v1/inputs?date=2020-01-01", headers=client_headers
    )
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_items_other_client(http_client, client_headers):
    await http_client.post(
        "/api/v1/inputs",
        json={"type": "text", "content": "mine", "date": TODAY},
        headers=client_headers,
    )
    other_headers = {"X-Client-ID": str(uuid.uuid4())}
    resp = await http_client.get(
        f"/api/v1/inputs?date={TODAY}", headers=other_headers
    )
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_get_item(http_client, client_headers):
    create = await http_client.post(
        "/api/v1/inputs",
        json={"type": "text", "content": "get me", "date": TODAY},
        headers=client_headers,
    )
    item_id = create.json()["id"]
    resp = await http_client.get(
        f"/api/v1/inputs/{item_id}", headers=client_headers
    )
    assert resp.status_code == 200
    assert resp.json()["content"] == "get me"


@pytest.mark.asyncio
async def test_get_item_not_found(http_client, client_headers):
    fake_id = str(uuid.uuid4())
    resp = await http_client.get(
        f"/api/v1/inputs/{fake_id}", headers=client_headers
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_item(http_client, client_headers):
    create = await http_client.post(
        "/api/v1/inputs",
        json={"type": "text", "content": "original", "date": TODAY},
        headers=client_headers,
    )
    item_id = create.json()["id"]
    resp = await http_client.put(
        f"/api/v1/inputs/{item_id}",
        json={"content": "updated"},
        headers=client_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["content"] == "updated"


@pytest.mark.asyncio
async def test_update_item_not_found(http_client, client_headers):
    fake_id = str(uuid.uuid4())
    resp = await http_client.put(
        f"/api/v1/inputs/{fake_id}",
        json={"content": "nope"},
        headers=client_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_item(http_client, client_headers):
    create = await http_client.post(
        "/api/v1/inputs",
        json={"type": "text", "content": "delete me", "date": TODAY},
        headers=client_headers,
    )
    item_id = create.json()["id"]
    resp = await http_client.delete(
        f"/api/v1/inputs/{item_id}", headers=client_headers
    )
    assert resp.status_code == 204

    get_resp = await http_client.get(
        f"/api/v1/inputs/{item_id}", headers=client_headers
    )
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_item_not_found(http_client, client_headers):
    fake_id = str(uuid.uuid4())
    resp = await http_client.delete(
        f"/api/v1/inputs/{fake_id}", headers=client_headers
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_clear_day(http_client, client_headers):
    await http_client.post(
        "/api/v1/inputs",
        json={"type": "text", "content": "a", "date": TODAY},
        headers=client_headers,
    )
    await http_client.post(
        "/api/v1/inputs",
        json={"type": "text", "content": "b", "date": TODAY},
        headers=client_headers,
    )
    resp = await http_client.delete(
        f"/api/v1/inputs?date={TODAY}", headers=client_headers
    )
    assert resp.status_code == 204

    list_resp = await http_client.get(
        f"/api/v1/inputs?date={TODAY}", headers=client_headers
    )
    assert list_resp.json() == []


@pytest.mark.asyncio
async def test_clear_day_does_not_affect_other_dates(http_client, client_headers):
    await http_client.post(
        "/api/v1/inputs",
        json={"type": "text", "content": "keep", "date": "2020-06-15"},
        headers=client_headers,
    )
    await http_client.post(
        "/api/v1/inputs",
        json={"type": "text", "content": "remove", "date": TODAY},
        headers=client_headers,
    )
    await http_client.delete(
        f"/api/v1/inputs?date={TODAY}", headers=client_headers
    )
    resp = await http_client.get(
        "/api/v1/inputs?date=2020-06-15", headers=client_headers
    )
    assert len(resp.json()) == 1
    assert resp.json()[0]["content"] == "keep"
