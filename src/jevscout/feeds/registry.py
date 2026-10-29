"""Unified registry and auto-detection for career site feeds."""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import urlsplit

from jevscout.feeds.ashby import parse_ashby_feed
from jevscout.feeds.greenhouse import parse_greenhouse_feed
from jevscout.feeds.lever import parse_lever_feed


def detect_feed_type(payload_json: str, source_url: str | None = None) -> str | None:
    """Detect whether a feed payload and/or source URL belongs to Greenhouse, Lever, or Ashby."""
    # 1. URL-based detection
    if source_url:
        host = (urlsplit(source_url).hostname or "").lower()
        if "greenhouse.io" in host:
            return "greenhouse"
        if "lever.co" in host:
            return "lever"
        if "ashbyhq.com" in host:
            return "ashby"

    # 2. Payload heuristics
    try:
        data = json.loads(payload_json)
    except (json.JSONDecodeError, RecursionError, TypeError):
        return None

    if isinstance(data, list):
        if data and isinstance(data[0], dict) and ("hostedUrl" in data[0] or "workplaceType" in data[0]):
            return "lever"

    if isinstance(data, dict):
        jobs = data.get("jobs")
        if isinstance(jobs, list) and jobs and isinstance(jobs[0], dict):
            first_job = jobs[0]
            if "absolute_url" in first_job or "departments" in first_job or "offices" in first_job:
                return "greenhouse"
            if "jobUrl" in first_job or "isRemote" in first_job or "secondaryLocations" in first_job:
                return "ashby"

    return None


def detect_and_parse_feed(
    payload_json: str,
    source_url: str,
    artifact_ref: str,
    india_only: bool = True,
) -> list[dict[str, Any]]:
    """Detect the feed type and extract structured JobPosting records."""
    feed_type = detect_feed_type(payload_json, source_url)

    if feed_type == "greenhouse":
        return parse_greenhouse_feed(payload_json, source_url, artifact_ref, india_only=india_only)
    if feed_type == "lever":
        return parse_lever_feed(payload_json, source_url, artifact_ref, india_only=india_only)
    if feed_type == "ashby":
        return parse_ashby_feed(payload_json, source_url, artifact_ref, india_only=india_only)

    return []
