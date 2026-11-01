"""Parser for Remote OK's public job JSON feed."""

from __future__ import annotations

import datetime
import json
import logging
from typing import Any

from jevscout.adapters.sources.location import is_india_eligible, normalize_india_location
from jevscout.adapters.sources.quality import sanitize_description
from jevscout.modules.jobs.extraction import _safe_url, _salary_display, _text

logger = logging.getLogger("jevscout.adapters.sources.remoteok")

PARSER_VERSION = "feed-remoteok-v1"
SOURCE_NAME = "Remote OK"


def parse_remoteok_feed(
    payload_json: str,
    source_url: str,
    artifact_ref: str,
    india_only: bool = True,
) -> list[dict[str, Any]]:
    """Parse Remote OK JSON while preserving source attribution and job links.

    Location is left unknown when the feed gives no location. The API's ``dev``
    tag is a seed filter, not proof that every returned role is a software job.
    """
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
        title = _text(item.get("position"))
        if not title:
            continue

        raw_location = _text(item.get("location")) or None
        india = is_india_eligible(raw_location or "")
        if india_only and not india:
            continue

        # Remote OK explicitly requires a follow link to Remote OK and a link
        # to the individual original posting. Store both in each parsed record.
        job_url = _safe_url(item.get("url"), "https://remoteok.com")
        if not job_url:
            job_url = _safe_url(item.get("apply_url"), "https://remoteok.com")
        if not job_url:
            continue

        posted = _text(item.get("date"))
        if not posted:
            epoch = item.get("epoch")
            if isinstance(epoch, (int, float)) and not isinstance(epoch, bool):
                try:
                    posted = datetime.datetime.fromtimestamp(
                        epoch, tz=datetime.timezone.utc
                    ).isoformat()
                except (ValueError, OverflowError, OSError):
                    pass

        location_normalized = (
            normalize_india_location(raw_location) if india and raw_location else raw_location
        )
        results.append(
            {
                "schema_version": 1,
                "parser_version": PARSER_VERSION,
                "title": title,
                "salary": _salary_display(
                    {"min": item.get("salary_min"), "max": item.get("salary_max")}
                    if item.get("salary_min") or item.get("salary_max")
                    else None
                ),
                "company": _text(item.get("company")),
                "location": raw_location,
                "location_normalized": location_normalized,
                "is_india": india,
                "description": sanitize_description(item.get("description")),
                "application_url": _safe_url(item.get("apply_url"), job_url) or job_url,
                "listing_url": job_url,
                "original_job_url": job_url,
                "date_posted": posted,
                "source_name": SOURCE_NAME,
                "source_url": source_url,
                "source_link": "https://remoteok.com/?ref=jevscout",
                "artifact_ref": artifact_ref,
            }
        )

    logger.debug(
        "parsed remoteok feed artifact_ref=%s total=%d retained=%d",
        artifact_ref,
        len(data),
        len(results),
    )
    return results
