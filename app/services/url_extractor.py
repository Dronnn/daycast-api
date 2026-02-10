import httpx
import trafilatura

MAX_EXTRACTED_LENGTH = 2000
FETCH_TIMEOUT = 15


async def extract_text_from_url(url: str) -> tuple[str | None, str | None]:
    """Fetch URL and extract main text content.

    Returns (extracted_text, error). On success error is None,
    on failure extracted_text is None.
    """
    try:
        async with httpx.AsyncClient(
            follow_redirects=True, timeout=FETCH_TIMEOUT
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()
    except httpx.HTTPError as e:
        return None, f"Fetch failed: {e}"

    text = trafilatura.extract(resp.text)
    if not text:
        return None, "No content extracted"
    return text[:MAX_EXTRACTED_LENGTH], None
