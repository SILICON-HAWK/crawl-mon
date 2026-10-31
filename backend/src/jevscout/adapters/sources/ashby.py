"""Ashby public job posting API parser with India location filtering."""

from __future__ import annotations

import json
import logging
from typing import Any

from jevscout.modules.jobs.extraction import _safe_url, _salary_display, _text
from jevscout.adapters.sources.location import is_india_eligible, normalize_india_location
from jevscout.adapters.sources.quality import sanitize_description

logger = logging.getLogger("jevscout.adapters.sources.ashby")

PARSER_VERSION = "feed-ashby-v1"


def parse_ashby_feed(
    payload_json: str,
    source_url: str,
    artifact_ref: str,
    india_only: bool = True,
) -> list[dict[str, Any]]:
    """Parse Ashby public job board JSON, optionally filtering strictly for India."""
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

        primary_loc = _text(item.get("location")) or ""
        is_remote = bool(item.get("isRemote"))

        # Check secondary locations
        secondary_locs = item.get("secondaryLocations")
        secondary_names: list[str] = []
        if isinstance(secondary_locs, list):
            for sec in secondary_locs:
                if isinstance(sec, dict):
                    loc_val = _text(sec.get("location"))
                    if loc_val:
                        secondary_names.append(loc_val)

        # Check eligibility
        is_india = is_india_eligible(primary_loc, workplace_type="remote" if is_remote else None)
        active_location = primary_loc

        # If primary wasn't India, check secondary locations
        if not is_india and secondary_names:
            for sec_name in secondary_names:
                if is_india_eligible(sec_name):
                    is_india = True
                    active_location = sec_name
                    break

        if india_only and not is_india:
            continue

        normalized_loc = normalize_india_location(active_location) if is_india else (active_location or None)

        department = _text(item.get("department"))
        description = sanitize_description(item.get("descriptionHtml"))

        app_url = _safe_url(item.get("jobUrl"), source_url)
        if not app_url:
            app_url = _safe_url(source_url, source_url)

        date_posted = _text(item.get("publishedAt"))
        compensation = item.get("compensation")
        salary = _salary_display(
            compensation.get("compensationTierSummary") or compensation.get("compensation")
            if isinstance(compensation, dict) else None
        )

        results.append(
            {
                "schema_version": 1,
                "parser_version": PARSER_VERSION,
                "title": title,
                "salary": salary,
                "company": department,
                "location": active_location or None,
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
        "parsed ashby feed artifact_ref=%s total=%d filtered_india=%d",
        artifact_ref,
        len(raw_jobs),
        len(results),
    )
    return results
