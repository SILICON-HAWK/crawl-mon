"""Lever public postings API parser with India location filtering."""

from __future__ import annotations

import datetime
import json
import logging
from typing import Any

from jevscout.modules.jobs.extraction import _safe_url, _salary_display, _text
from jevscout.adapters.sources.location import is_india_eligible, normalize_india_location
from jevscout.adapters.sources.quality import sanitize_description

logger = logging.getLogger("jevscout.adapters.sources.lever")

PARSER_VERSION = "feed-lever-v1"


def parse_lever_feed(
    payload_json: str,
    source_url: str,
    artifact_ref: str,
    india_only: bool = True,
) -> list[dict[str, Any]]:
    """Parse Lever public postings JSON array, optionally filtering strictly for India."""
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

        raw_title = item.get("text")
        title = _text(raw_title) if raw_title else None
        if not title:
            continue

        categories = item.get("categories")
        raw_location = ""
        team = None
        if isinstance(categories, dict):
            raw_location = _text(categories.get("location")) or ""
            team = _text(categories.get("team"))

        workplace_type = _text(item.get("workplaceType"))

        # Check location eligibility
        is_india = is_india_eligible(raw_location, workplace_type=workplace_type)

        # Fallback: also check if title has explicit India tag e.g. "(India Remote)"
        if not is_india and title and is_india_eligible(title):
            is_india = True

        if india_only and not is_india:
            continue

        normalized_loc = normalize_india_location(raw_location) if is_india else raw_location

        # Description: prefer descriptionPlain if available, otherwise description HTML
        raw_desc = item.get("descriptionPlain") or item.get("description")
        description = sanitize_description(raw_desc)

        # URL
        app_url = _safe_url(item.get("hostedUrl"), source_url)
        if not app_url:
            app_url = _safe_url(source_url, source_url)

        # Date posted
        date_posted = None
        created_at_ms = item.get("createdAt")
        if isinstance(created_at_ms, (int, float)) and created_at_ms > 0:
            try:
                dt = datetime.datetime.fromtimestamp(created_at_ms / 1000.0, tz=datetime.timezone.utc)
                date_posted = dt.isoformat()
            except (ValueError, OverflowError):
                pass

        results.append(
            {
                "schema_version": 1,
                "parser_version": PARSER_VERSION,
                "title": title,
                "salary": _salary_display(item.get("salaryDescription") or item.get("salaryRange")),
                "company": team,
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
        "parsed lever feed artifact_ref=%s total=%d filtered_india=%d",
        artifact_ref,
        len(data),
        len(results),
    )
    return results
