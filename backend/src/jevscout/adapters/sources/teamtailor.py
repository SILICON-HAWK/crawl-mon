"""Teamtailor public jobs JSON API parser with India location filtering."""

from __future__ import annotations

import json
import logging
from typing import Any

from jevscout.modules.jobs.extraction import _safe_url, _text
from jevscout.adapters.sources.location import is_india_eligible, normalize_india_location
from jevscout.adapters.sources.quality import sanitize_description

logger = logging.getLogger("jevscout.adapters.sources.teamtailor")

PARSER_VERSION = "feed-teamtailor-v1"


def parse_teamtailor_feed(
    payload_json: str,
    source_url: str,
    artifact_ref: str,
    india_only: bool = True,
) -> list[dict[str, Any]]:
    """Parse Teamtailor public jobs JSON array, optionally filtering strictly for India."""
    try:
        data = json.loads(payload_json)
    except (json.JSONDecodeError, RecursionError, TypeError):
        return []

    if not isinstance(data, list):
        return []

    results: list[dict[str, Any]] = []

    for item in data:
        if not isinstance(item, dict):
            continue

        raw_title = item.get("title")
        title = _text(raw_title) if raw_title else None
        if not title:
            continue

        raw_location = ""
        loc_val = item.get("locations") or item.get("location")
        if isinstance(loc_val, str):
            raw_location = _text(loc_val) or ""
        elif isinstance(loc_val, list):
            parts = [_text(x) for x in loc_val if _text(x)]
            raw_location = ", ".join(parts)

        remote_status = _text(item.get("remote_status"))
        is_remote = bool(remote_status and remote_status.lower() in ("remote", "hybrid"))

        # Check location eligibility
        is_india = is_india_eligible(raw_location, workplace_type="remote" if is_remote else None)
        if not is_india and title and is_india_eligible(title):
            is_india = True

        if india_only and not is_india:
            continue

        normalized_loc = normalize_india_location(raw_location) if is_india else (raw_location or None)

        department = _text(item.get("department"))
        body_content = item.get("body") or item.get("description")
        description = sanitize_description(body_content)

        app_url = _safe_url(item.get("url"), source_url)
        if not app_url:
            app_url = _safe_url(source_url, source_url)

        date_posted = _text(item.get("created_at"))

        results.append(
            {
                "schema_version": 1,
                "parser_version": PARSER_VERSION,
                "title": title,
                "company": department,
                "location": raw_location or None,
                "location_normalized": normalized_loc,
                "is_india": is_india,
                "description": description,
                "application_url": app_url,
                "date_posted": date_posted,
                "source_url": source_url,
                "artifact_ref": artifact_ref,
            }
        )

    logger.debug(
        "parsed teamtailor feed artifact_ref=%s total=%d filtered_india=%d",
        artifact_ref,
        len(data),
        len(results),
    )
    return results
