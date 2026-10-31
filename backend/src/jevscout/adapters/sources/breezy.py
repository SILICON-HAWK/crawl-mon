"""Breezy HR public board API parser with India location filtering."""

from __future__ import annotations

import json
import logging
from typing import Any

from jevscout.modules.jobs.extraction import _safe_url, _salary_display, _text
from jevscout.adapters.sources.location import is_india_eligible, normalize_india_location
from jevscout.adapters.sources.quality import sanitize_description

logger = logging.getLogger("jevscout.adapters.sources.breezy")

PARSER_VERSION = "feed-breezy-v1"


def parse_breezy_feed(
    payload_json: str,
    source_url: str,
    artifact_ref: str,
    india_only: bool = True,
) -> list[dict[str, Any]]:
    """Parse Breezy HR public postings JSON array, optionally filtering strictly for India."""
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

        raw_title = item.get("name")
        title = _text(raw_title) if raw_title else None
        if not title:
            continue

        loc_obj = item.get("location")
        raw_location = ""
        is_remote = False
        if isinstance(loc_obj, dict):
            raw_location = _text(loc_obj.get("name")) or ""
            is_remote = bool(loc_obj.get("is_remote"))
            if not raw_location:
                city = _text(loc_obj.get("city"))
                state = _text(loc_obj.get("state"))
                country = None
                country_dict = loc_obj.get("country")
                if isinstance(country_dict, dict):
                    country = _text(country_dict.get("name"))
                parts = [p for p in (city, state, country) if p]
                if parts:
                    raw_location = ", ".join(parts)

        is_india = is_india_eligible(raw_location, workplace_type="remote" if is_remote else None)
        if not is_india and title and is_india_eligible(title):
            is_india = True

        if india_only and not is_india:
            continue

        normalized_loc = normalize_india_location(raw_location) if is_india else (raw_location or None)

        department = _text(item.get("department"))
        description = sanitize_description(item.get("description"))

        app_url = _safe_url(item.get("url"), source_url)
        if not app_url:
            app_url = _safe_url(source_url, source_url)

        date_posted = _text(item.get("published_date"))

        results.append(
            {
                "schema_version": 1,
                "parser_version": PARSER_VERSION,
                "title": title,
                "salary": _salary_display(item.get("salary") or item.get("salary_range")),
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
        "parsed breezy feed artifact_ref=%s total=%d filtered_india=%d",
        artifact_ref,
        len(data),
        len(results),
    )
    return results
