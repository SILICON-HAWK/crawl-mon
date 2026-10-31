"""Greenhouse public board API parser with India location filtering."""

from __future__ import annotations

import json
import logging
from html import unescape
from typing import Any

from jevscout.modules.jobs.extraction import _safe_url, _text
from jevscout.adapters.sources.location import is_india_eligible, normalize_india_location
from jevscout.adapters.sources.quality import sanitize_description

logger = logging.getLogger("jevscout.adapters.sources.greenhouse")

PARSER_VERSION = "feed-greenhouse-v1"


def parse_greenhouse_feed(
    payload_json: str,
    source_url: str,
    artifact_ref: str,
    india_only: bool = True,
) -> list[dict[str, Any]]:
    """Parse Greenhouse public board jobs JSON, optionally filtering strictly for India."""
    try:
        data = json.loads(payload_json)
    except (json.JSONDecodeError, RecursionError, TypeError):
        return []

    if not isinstance(data, dict):
        return []

    raw_jobs = data.get("jobs")
    if not isinstance(raw_jobs, list):
        return []

    results: list[dict[str, Any]] = []

    for item in raw_jobs:
        if not isinstance(item, dict):
            continue

        raw_title = item.get("title")
        title = _text(raw_title) if raw_title else None
        if not title:
            continue

        # Extract location
        loc_obj = item.get("location")
        raw_location = ""
        if isinstance(loc_obj, dict):
            raw_location = _text(loc_obj.get("name")) or ""

        # Secondary location checks from offices
        offices = item.get("offices")
        office_names = []
        if isinstance(offices, list):
            for off in offices:
                if isinstance(off, dict):
                    name = off.get("name") or off.get("location")
                    if isinstance(name, str) and name.strip():
                        office_names.append(name.strip())

        full_location_str = raw_location
        if office_names and not raw_location:
            full_location_str = ", ".join(office_names)

        is_india = is_india_eligible(full_location_str)
        if not is_india and office_names:
            is_india = any(is_india_eligible(off) for off in office_names)

        if india_only and not is_india:
            continue

        normalized_loc = normalize_india_location(full_location_str) if is_india else full_location_str

        # Company / Department
        departments = item.get("departments")
        department_name = None
        if isinstance(departments, list) and departments:
            first_dept = departments[0]
            if isinstance(first_dept, dict):
                department_name = _text(first_dept.get("name"))

        # Description / Content
        raw_content = item.get("content")
        description = None
        if isinstance(raw_content, str):
            # Greenhouse content can contain escaped HTML entities
            description = sanitize_description(unescape(raw_content))

        # URL
        app_url = _safe_url(item.get("absolute_url"), source_url)
        if not app_url:
            app_url = _safe_url(source_url, source_url)

        date_posted = _text(item.get("updated_at"))

        results.append(
            {
                "schema_version": 1,
                "parser_version": PARSER_VERSION,
                "title": title,
                "company": department_name,  # Or board name from context
                "location": full_location_str or None,
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
        "parsed greenhouse feed artifact_ref=%s total=%d filtered_india=%d",
        artifact_ref,
        len(raw_jobs),
        len(results),
    )
    return results
