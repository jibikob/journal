import re
from typing import Any


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "untitled"


def extract_editorjs_text(content_json: dict[str, Any] | None) -> str:
    if not content_json:
        return ""

    blocks = content_json.get("blocks", [])
    parts: list[str] = []

    for block in blocks:
        data = block.get("data") or {}
        for key in ("text", "caption", "title", "message"):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                cleaned = re.sub(r"<[^>]+>", "", value).strip()
                if cleaned:
                    parts.append(cleaned)

        items = data.get("items")
        if isinstance(items, list):
            for item in items:
                if isinstance(item, str):
                    cleaned = re.sub(r"<[^>]+>", "", item).strip()
                    if cleaned:
                        parts.append(cleaned)

    return "\n".join(parts)
