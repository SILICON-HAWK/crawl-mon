"""Pure extraction of schema.org JobPosting records from saved HTML."""

from __future__ import annotations

import json
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit


_MAX_JSON_DEPTH = 64
_MAX_JSON_NODES = 10000


class _JsonLdScripts(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.scripts: list[str] = []
        self._script_type: str | None = None
        self._script_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "script":
            return
        attributes = {name.lower(): value for name, value in attrs}
        media_type = (attributes.get("type") or "").split(";", 1)[0].strip().lower()
        self._script_type = media_type if media_type == "application/ld+json" else None
        self._script_parts = []

    def handle_data(self, data: str) -> None:
        if self._script_type:
            self._script_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "script":
            if self._script_type:
                self.scripts.append("".join(self._script_parts))
            self._script_type = None
            self._script_parts = []


class _PlainText(HTMLParser):
    _BLOCK_TAGS = {"address", "article", "blockquote", "br", "div", "li", "p", "section"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in self._BLOCK_TAGS:
            self.parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in self._BLOCK_TAGS:
            self.parts.append(" ")


def _text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    parser = _PlainText()
    try:
        parser.feed(value)
        parser.close()
    except (AssertionError, ValueError):
        pass
    result = " ".join("".join(parser.parts).split())
    return result or None


def _is_job_posting(value: object) -> bool:
    types = value.get("@type") if isinstance(value, dict) else None
    if isinstance(types, str):
        return types.rsplit("/", 1)[-1].rsplit("#", 1)[-1] == "JobPosting"
    if isinstance(types, list):
        return any(
            isinstance(item, str)
            and item.rsplit("/", 1)[-1].rsplit("#", 1)[-1] == "JobPosting"
            for item in types
        )
    return False


def _posting_records(value: object):
    """Yield posting nodes from roots and @graph, with bounded traversal."""
    stack: list[tuple[object, int]] = [(value, 0)]
    visited = 0
    while stack and visited < _MAX_JSON_NODES:
        node, depth = stack.pop()
        visited += 1
        if depth > _MAX_JSON_DEPTH:
            continue
        if isinstance(node, list):
            stack.extend((item, depth + 1) for item in reversed(node))
        elif isinstance(node, dict):
            if _is_job_posting(node):
                yield node
            graph = node.get("@graph")
            if isinstance(graph, (dict, list)):
                stack.append((graph, depth + 1))


def _location(value: object) -> str | None:
    places = value if isinstance(value, list) else [value]
    for place in places:
        if not isinstance(place, dict):
            continue
        address = place.get("address")
        if not isinstance(address, dict):
            continue
        fields = []
        for key in ("addressLocality", "addressRegion", "addressCountry"):
            field = address.get(key)
            if isinstance(field, dict):
                field = field.get("name") or field.get("addressCountry")
            cleaned = _text(field)
            if cleaned and cleaned not in fields:
                fields.append(cleaned)
        if fields:
            return ", ".join(fields)
    return None


def _safe_url(value: object, source_url: str) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    if any(
        char.isspace() or char == "\\" or ord(char) < 32 or 127 <= ord(char) <= 159
        for char in value
    ):
        return None
    try:
        resolved = urljoin(source_url, value)
        parsed = urlsplit(resolved)
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
            return None
        if parsed.username is not None or parsed.password is not None:
            return None
        parsed.port  # Access validates malformed and out-of-range ports.
        return resolved
    except ValueError:
        return None


def _record(posting: dict[str, object], source_url: str, artifact_ref: str) -> dict:
    title = _text(posting.get("name")) or _text(posting.get("title"))
    if not title:
        raise ValueError("JobPosting has no usable title")

    organization = posting.get("hiringOrganization")
    company = _text(organization.get("name")) if isinstance(organization, dict) else None

    application_url = _safe_url(posting.get("url"), source_url)
    if "url" not in posting:
        application_url = _safe_url(source_url, source_url)

    return {
        "schema_version": 1,
        "parser_version": "jsonld-jobs-v1",
        "title": title,
        "company": company,
        "location": _location(posting.get("jobLocation")),
        "description": _text(posting.get("description")),
        "application_url": application_url,
        "date_posted": _text(posting.get("datePosted")),
        "source_url": source_url,
        "artifact_ref": artifact_ref,
    }


def parse_jobs(html: str, source_url: str, artifact_ref: str) -> list[dict]:
    """Extract schema.org JobPosting JSON-LD from an already-saved HTML string."""
    scripts = _JsonLdScripts()
    scripts.feed(html)
    scripts.close()

    jobs = []
    for script in scripts.scripts:
        try:
            document = json.loads(script)
        except (json.JSONDecodeError, RecursionError):
            continue
        for posting in _posting_records(document):
            try:
                jobs.append(_record(posting, source_url, artifact_ref))
            except ValueError:
                continue
    return jobs
