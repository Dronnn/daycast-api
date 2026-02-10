import base64
import json
import mimetypes
import time
from pathlib import Path

import httpx
import structlog

from app.config import settings
from app.services.file_storage import UPLOAD_DIR
from app.services.product_config import get_ai_config, get_channels, get_lengths

logger = structlog.get_logger()

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
PROMPT_TEMPLATE = (PROJECT_ROOT / "prompts" / "generate_v1.md").read_text()
REGENERATE_TEMPLATE = (PROJECT_ROOT / "prompts" / "regenerate_v1.md").read_text()

OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"


def _image_to_data_url(relative_path: str) -> str | None:
    """Read image from disk and return as base64 data URL for OpenAI vision."""
    file_path = UPLOAD_DIR / relative_path
    if not file_path.exists():
        logger.warning("image_not_found", path=str(file_path))
        return None
    mime, _ = mimetypes.guess_type(file_path.name)
    if not mime:
        mime = "image/jpeg"
    data = file_path.read_bytes()
    b64 = base64.b64encode(data).decode()
    return f"data:{mime};base64,{b64}"


def _build_items_block(items: list[dict]) -> str:
    """Build the items section for the prompt."""
    parts = []
    for i, item in enumerate(items, 1):
        if item["type"] == "text":
            parts.append(f"[{i}] Text: {item['content']}")
        elif item["type"] == "url":
            extracted = item.get("extracted_text") or "(extraction failed)"
            parts.append(f"[{i}] URL: {item['content']}\nExtracted content: {extracted}")
        elif item["type"] == "image":
            parts.append(f"[{i}] [Image — see attached]")
    return "\n\n".join(parts)


def _build_channels_block(
    channel_ids: list[str],
    style_override: str | None,
    language_override: str | None,
    channel_settings: dict[str, dict],
) -> str:
    """Build the channels section for the prompt."""
    all_channels = get_channels()
    all_lengths = get_lengths()
    parts = []
    for ch_id in channel_ids:
        ch = all_channels[ch_id]
        cs = channel_settings.get(ch_id, {})
        style = style_override or cs.get("default_style", "casual")
        language = language_override or cs.get("default_language", "ru")
        length_id = cs.get("default_length", "medium")
        length_desc = all_lengths.get(length_id, {}).get("description", "1-2 paragraphs, balanced")
        parts.append(
            f"- {ch_id}: {ch['name']} — {ch['description']}\n"
            f"  Style: {style} | Language: {language} | Length: {length_desc} | Max length: {ch['max_length']} chars"
        )
    return "\n".join(parts)


def _build_messages(
    items: list[dict],
    channel_ids: list[str],
    style_override: str | None,
    language_override: str | None,
    channel_settings: dict[str, dict],
) -> list[dict]:
    """Build OpenAI messages array, including vision for images."""
    items_block = _build_items_block(items)
    channels_block = _build_channels_block(
        channel_ids, style_override, language_override, channel_settings
    )
    prompt_text = PROMPT_TEMPLATE.replace("{items_block}", items_block).replace(
        "{channels_block}", channels_block
    )

    # Build content parts — text + any images (as base64 data URLs)
    content_parts: list[dict] = [{"type": "text", "text": prompt_text}]
    for item in items:
        if item["type"] == "image":
            data_url = _image_to_data_url(item["content"])
            if data_url:
                content_parts.append(
                    {
                        "type": "image_url",
                        "image_url": {"url": data_url, "detail": "low"},
                    }
                )

    return [{"role": "user", "content": content_parts}]


def _parse_ai_response(raw: str) -> list[dict]:
    """Parse and validate the JSON response from AI."""
    # Strip markdown code fences if present
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
    data = json.loads(text)
    results = data["results"]
    for r in results:
        if "channel_id" not in r or "text" not in r:
            raise ValueError("Missing channel_id or text in result")
    return results


async def generate(
    items: list[dict],
    channel_ids: list[str],
    style_override: str | None,
    language_override: str | None,
    channel_settings: dict[str, dict],
) -> tuple[list[dict], str, int]:
    """Call OpenAI and return (results, model_used, latency_ms).

    Retries up to 3 times on invalid JSON.
    """
    ai_config = get_ai_config()
    messages = _build_messages(
        items, channel_ids, style_override, language_override, channel_settings
    )

    last_error = None
    for attempt in range(ai_config["retries"]):
        start = time.monotonic()
        async with httpx.AsyncClient(timeout=ai_config["timeout_seconds"]) as client:
            resp = await client.post(
                OPENAI_CHAT_URL,
                headers={
                    "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": ai_config["model"],
                    "temperature": ai_config["temperature"],
                    "max_completion_tokens": ai_config["max_tokens"],
                    "messages": messages,
                },
            )
            resp.raise_for_status()

        latency_ms = int((time.monotonic() - start) * 1000)
        body = resp.json()
        raw_content = body["choices"][0]["message"]["content"]
        model_used = body.get("model", ai_config["model"])

        try:
            results = _parse_ai_response(raw_content)
            logger.info(
                "ai_generation_success",
                attempt=attempt + 1,
                latency_ms=latency_ms,
                channels=[r["channel_id"] for r in results],
            )
            return results, model_used, latency_ms
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            last_error = e
            logger.warning(
                "ai_invalid_json",
                attempt=attempt + 1,
                error=str(e),
                response_length=len(raw_content),
            )

    raise ValueError(f"AI returned invalid JSON after {ai_config['retries']} attempts: {last_error}")


def _build_previous_block(previous_results: list[dict]) -> str:
    """Build the previous generation section for regeneration prompt."""
    parts = []
    for r in previous_results:
        parts.append(f"- {r['channel_id']}: {r['text']}")
    return "\n".join(parts)


async def regenerate(
    items: list[dict],
    channel_ids: list[str],
    previous_results: list[dict],
    style_override: str | None,
    language_override: str | None,
    channel_settings: dict[str, dict],
) -> tuple[list[dict], str, int]:
    """Call OpenAI for regeneration and return (results, model_used, latency_ms)."""
    ai_config = get_ai_config()
    items_block = _build_items_block(items)
    channels_block = _build_channels_block(
        channel_ids, style_override, language_override, channel_settings
    )
    previous_block = _build_previous_block(previous_results)

    prompt_text = (
        REGENERATE_TEMPLATE
        .replace("{items_block}", items_block)
        .replace("{channels_block}", channels_block)
        .replace("{previous_block}", previous_block)
    )

    content_parts: list[dict] = [{"type": "text", "text": prompt_text}]
    for item in items:
        if item["type"] == "image":
            data_url = _image_to_data_url(item["content"])
            if data_url:
                content_parts.append(
                    {
                        "type": "image_url",
                        "image_url": {"url": data_url, "detail": "low"},
                    }
                )

    messages = [{"role": "user", "content": content_parts}]

    last_error = None
    for attempt in range(ai_config["retries"]):
        start = time.monotonic()
        async with httpx.AsyncClient(timeout=ai_config["timeout_seconds"]) as client:
            resp = await client.post(
                OPENAI_CHAT_URL,
                headers={
                    "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": ai_config["model"],
                    "temperature": ai_config["temperature"],
                    "max_completion_tokens": ai_config["max_tokens"],
                    "messages": messages,
                },
            )
            resp.raise_for_status()

        latency_ms = int((time.monotonic() - start) * 1000)
        body = resp.json()
        raw_content = body["choices"][0]["message"]["content"]
        model_used = body.get("model", ai_config["model"])

        try:
            results = _parse_ai_response(raw_content)
            logger.info(
                "ai_regeneration_success",
                attempt=attempt + 1,
                latency_ms=latency_ms,
                channels=[r["channel_id"] for r in results],
            )
            return results, model_used, latency_ms
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            last_error = e
            logger.warning(
                "ai_invalid_json",
                attempt=attempt + 1,
                error=str(e),
                response_length=len(raw_content),
            )

    raise ValueError(f"AI returned invalid JSON after {ai_config['retries']} attempts: {last_error}")
