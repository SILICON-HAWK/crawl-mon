"""Recruitee public offers API parser with India location filtering."""

from __future__ import annotations

import json
import logging
from typing import Any

from jevscout.modules.jobs.extraction import _safe_url, _text
from jevscout.adapters.sources.location import is_india_eligible, normalize_india_location
from jevscout.adapters.sources.quality import sanitize_description

logger = logging.getLogger("jevscout.adapters.sources.recruitee")

PARSER_VERSION = "feed-recruitee-v1"


def parse_recruitee_feed(
    payload_json: str,
    source_url: str,
    artifact_ref: str,
    india_only: bool = True,
) -> list[dict[str, Any]]:
    """Parse Recruitee public offers JSON, optionally filtering strictly for India."""
    try:
        data = json.loads(payload_json)
    except (json.JSONDecodeError, RecursionError, TypeError):
        return []

    if not isinstance(data, dict):
        return []

    offers = data.get("offers")
    if not isinstance(offers, list):
        return []

    results: list[dict[str, Any]] = []

    for item in offers:
        if not isinstance(item, dict):
            continue

        raw_title = item.get("title")
        title = _text(raw_title) if raw_title else None
        if not title:
            continue

        raw_location = _text(item.get("location")) or ""
        city = _text(item.get("city"))
        country_code = _text(item.get("country_code"))
        is_remote = bool(item.get("remote"))

        if not raw_location:
            parts = [p for p in (city, country_code) if p]
            if parts:
                raw_location = ", ".join(parts)

        # Check location eligibility
        is_india = is_india_eligible(raw_location, workplace_type="remote" if is_remote else None)
        if not is_india and country_code and country_code.upper() == "IN":
            is_india = True
        if not is_india and title and is_india_eligible(title):
            is_india = True

        if india_only and not is_india:
            continue

        normalized_loc = normalize_india_location(raw_location) if is_india else (raw_location or None)

        department = _text(item.get("department"))
        description = sanitize_description(item.get("description"))

        app_url = _safe_url(item.get("careers_url"), source_url)
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
        "parsed recruitee feed artifact_ref=%s total=%d filtered_india=%d",
        artifact_ref,
        len(offers),
        len(results),
    )
    return results
