"""Empirical quality guards, department explosion mitigation, and text sanitization."""

from __future__ import annotations

import logging
import re
from typing import Optional

from jevscout.extraction import _text

logger = logging.getLogger("jevscout.feeds.quality")

_MAX_DEPARTMENTS_THRESHOLD = 25

# Strips URLs (http, https, //cdn...), email addresses, and share button noise
_URL_REGEX = re.compile(r"(https?://\S+|//\S+)", re.IGNORECASE)
_EMAIL_REGEX = re.compile(r"[\w\.-]+@[\w\.-]+\.\w+", re.IGNORECASE)

# Keywords indicating an inherently technical posting
_TECH_TITLE_REGEX = re.compile(
    r"\b(engineer|developer|architect|devops|sre|platform|infrastructure|data|"
    r"software|backend|frontend|full\s*stack|qa|test|security|machine\s*learning|"
    r"ai|ml|cloud|database|systems|embedded|mobile|ios|android|product\s*manager|"
    r"analyst|webmaster|programmer)\b",
    re.IGNORECASE,
)

_TECH_DEPT_REGEX = re.compile(
    r"\b(engineering|technology|r&d|product|infrastructure|devops|data|platform|information\s*technology|it)\b",
    re.IGNORECASE,
)


def sanitize_description(html_or_text: str | None) -> str | None:
    """Strip CDN asset URLs, emojis, email addresses, and HTML tags from descriptions."""
    if not html_or_text or not html_or_text.strip():
        return None

    cleaned = _URL_REGEX.sub(" ", html_or_text)
    cleaned = _EMAIL_REGEX.sub(" ", cleaned)
    # Use standard text cleaner to remove HTML tags and normalize whitespace
    result = _text(cleaned)
    return result


def is_technical_posting(title: str | None, department: str | None = None) -> bool:
    """Verify if a posting's title or department represents a technical role.

    This prevents non-tech acronym false positives (e.g., 'dbt' in clinical therapy or 'PHP' in psychiatric clinics).
    """
    if not title:
        return False

    if _TECH_TITLE_REGEX.search(title):
        return True

    if department and _TECH_DEPT_REGEX.search(department):
        return True

    return False


def clean_department(department: str | None, total_departments: int = 1) -> Optional[str]:
    """Clean department name, suppressing grouping if the board has >25 departments (subteam/branch codes)."""
    if not department or not department.strip():
        return None

    clean_dept = department.strip()

    if total_departments > _MAX_DEPARTMENTS_THRESHOLD:
        logger.debug(
            "suppressing department grouping (board has %d departments, exceeding threshold %d): '%s'",
            total_departments,
            _MAX_DEPARTMENTS_THRESHOLD,
            clean_dept,
        )
        return None

    return clean_dept
