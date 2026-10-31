"""Unified registry and auto-detection for career site feeds."""

from __future__ import annotations

import json
import logging
from typing import Any
from urllib.parse import urlsplit

from jevscout.feeds.ashby import parse_ashby_feed
from jevscout.feeds.breezy import parse_breezy_feed
from jevscout.feeds.greenhouse import parse_greenhouse_feed
from jevscout.feeds.lever import parse_lever_feed
from jevscout.feeds.recruitee import parse_recruitee_feed
from jevscout.feeds.teamtailor import parse_teamtailor_feed

logger = logging.getLogger("jevscout.feeds.registry")


def detect_feed_type(payload_json: str, source_url: str | None = None) -> str | None:
    """Detect whether a feed payload and/or source URL belongs to Greenhouse, Lever, Ashby, Breezy, Recruitee, or Teamtailor."""
    # 1. URL-based detection
    if source_url:
        host = (urlsplit(source_url).hostname or "").lower()
        if "greenhouse.io" in host:
            return "greenhouse"
        if "lever.co" in host:
            return "lever"
        if "ashbyhq.com" in host:
            return "ashby"
        if "breezy.hr" in host:
            return "breezy"
        if "recruitee.com" in host:
            return "recruitee"
        if "teamtailor.com" in host:
            return "teamtailor"

    # 2. Payload heuristics
    try:
        data = json.loads(payload_json)
    except (json.JSONDecodeError, RecursionError, TypeError):
        return None

    if isinstance(data, list):
        if data and isinstance(data[0], dict):
            first_item = data[0]
            if "hostedUrl" in first_item or "workplaceType" in first_item:
                return "lever"
            if "published_date" in first_item and ("type" in first_item or "location" in first_item):
                return "breezy"
            if "remote_status" in first_item or ("locations" in first_item and "body" in first_item):
                return "teamtailor"

    if isinstance(data, dict):
        if "offers" in data and isinstance(data.get("offers"), list):
            return "recruitee"
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
    if feed_type == "breezy":
        return parse_breezy_feed(payload_json, source_url, artifact_ref, india_only=india_only)
    if feed_type == "recruitee":
        return parse_recruitee_feed(payload_json, source_url, artifact_ref, india_only=india_only)
    if feed_type == "teamtailor":
        return parse_teamtailor_feed(payload_json, source_url, artifact_ref, india_only=india_only)

    logger.debug("no recognized career feed detected artifact_ref=%s", artifact_ref)
    return []
