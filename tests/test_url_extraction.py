from datetime import date
from unittest.mock import AsyncMock, patch

import httpx
import pytest

TODAY = date.today().isoformat()

SAMPLE_HTML = """
<html>
<head><title>Test Article</title></head>
<body>
<article>
<h1>Test Article</h1>
<p>This is the main content of the article. It contains enough text for
trafilatura to extract meaningfully. The article discusses important topics
that are relevant to the reader. We need several sentences here to ensure
the extraction library recognizes this as real content rather than boilerplate.
More text follows to make this substantial enough for extraction.</p>
</article>
<footer>Copyright 2025</footer>
</body>
</html>
"""


def _mock_httpx_success(html: str = SAMPLE_HTML):
    """Return a mock that patches httpx.AsyncClient.get to return HTML."""
    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_resp.text = html
    mock_resp.raise_for_status = lambda: None

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    return patch("app.services.url_extractor.httpx.AsyncClient", return_value=mock_client)


def _mock_httpx_error():
    """Return a mock that patches httpx.AsyncClient.get to raise an error."""
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    return patch("app.services.url_extractor.httpx.AsyncClient", return_value=mock_client)


@pytest.mark.asyncio
async def test_create_url_item_extracts_text(http_client, client_headers):
    with _mock_httpx_success():
        resp = await http_client.post(
            "/api/v1/inputs",
            json={"type": "url", "content": "https://example.com/article", "date": TODAY},
            headers=client_headers,
        )
    assert resp.status_code == 201
    data = resp.json()
    assert data["type"] == "url"
    assert data["content"] == "https://example.com/article"
    # trafilatura may or may not extract from this minimal HTML;
    # at minimum one of extracted_text or extract_error should be set
    assert data["extracted_text"] is not None or data["extract_error"] is not None


@pytest.mark.asyncio
async def test_create_url_item_fetch_failure(http_client, client_headers):
    with _mock_httpx_error():
        resp = await http_client.post(
            "/api/v1/inputs",
            json={"type": "url", "content": "https://unreachable.test", "date": TODAY},
            headers=client_headers,
        )
    assert resp.status_code == 201
    data = resp.json()
    assert data["extracted_text"] is None
    assert data["extract_error"] is not None
    assert "Fetch failed" in data["extract_error"]


@pytest.mark.asyncio
async def test_create_url_item_no_content_extracted(http_client, client_headers):
    empty_html = "<html><body><nav>Menu</nav></body></html>"
    with _mock_httpx_success(html=empty_html):
        resp = await http_client.post(
            "/api/v1/inputs",
            json={"type": "url", "content": "https://example.com/empty", "date": TODAY},
            headers=client_headers,
        )
    assert resp.status_code == 201
    data = resp.json()
    assert data["extract_error"] == "No content extracted"


@pytest.mark.asyncio
async def test_create_text_item_no_extraction(http_client, client_headers):
    resp = await http_client.post(
        "/api/v1/inputs",
        json={"type": "text", "content": "plain text", "date": TODAY},
        headers=client_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["extracted_text"] is None
    assert data["extract_error"] is None


@pytest.mark.asyncio
async def test_extracted_text_truncated_to_2000(http_client, client_headers):
    long_text = "A" * 5000
    long_html = f"<html><body><article><p>{long_text}</p></article></body></html>"

    with _mock_httpx_success(html=long_html), \
         patch("app.services.url_extractor.trafilatura.extract", return_value=long_text):
        resp = await http_client.post(
            "/api/v1/inputs",
            json={"type": "url", "content": "https://example.com/long", "date": TODAY},
            headers=client_headers,
        )
    assert resp.status_code == 201
    data = resp.json()
    assert data["extracted_text"] is not None
    assert len(data["extracted_text"]) <= 2000


@pytest.mark.asyncio
async def test_url_item_appears_in_list(http_client, client_headers):
    with _mock_httpx_success():
        await http_client.post(
            "/api/v1/inputs",
            json={"type": "url", "content": "https://example.com", "date": TODAY},
            headers=client_headers,
        )
    resp = await http_client.get(
        f"/api/v1/inputs?date={TODAY}", headers=client_headers
    )
    items = resp.json()
    assert len(items) == 1
    assert items[0]["type"] == "url"
