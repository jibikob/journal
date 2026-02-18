import re
from html.parser import HTMLParser
from typing import Any


class _WikiLinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[dict[str, Any]] = []
        self._active_link: dict[str, Any] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return

        attrs_dict = dict(attrs)
        article_id_raw = attrs_dict.get("data-article-id")
        if not article_id_raw:
            return

        try:
            article_id = int(article_id_raw)
        except ValueError:
            return

        self._active_link = {"to_article_id": article_id, "anchor": ""}

    def handle_data(self, data: str) -> None:
        if self._active_link is None:
            return
        self._active_link["anchor"] += data

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() != "a" or self._active_link is None:
            return

        anchor = self._active_link["anchor"].strip()
        if anchor:
            self.links.append({"to_article_id": self._active_link["to_article_id"], "anchor": anchor})
        self._active_link = None


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


def extract_wiki_links(content_json: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not content_json:
        return []

    parser = _WikiLinkParser()
    for block in content_json.get("blocks", []):
        data = block.get("data") or {}
        for key in ("text", "caption", "title", "message"):
            value = data.get(key)
            if isinstance(value, str) and "data-article-id" in value:
                parser.feed(value)

        items = data.get("items")
        if isinstance(items, list):
            for item in items:
                if isinstance(item, str) and "data-article-id" in item:
                    parser.feed(item)

    deduped: dict[tuple[int, str], dict[str, Any]] = {}
    for link in parser.links:
        key = (link["to_article_id"], link["anchor"])
        deduped[key] = link

    return list(deduped.values())
