"""Common Crawl CDX token harvester for discovering public ATS board tokens."""

from __future__ import annotations

import logging
import re
from typing import Iterable, Optional

logger = logging.getLogger("jevscout.feeds.harvester")

# Reserved path segments and subdomains that are not company slugs
RESERVED_TOKENS = {
    "api",
    "app",
    "assets",
    "auth",
    "blog",
    "cdn",
    "careers",
    "css",
    "docs",
    "embed",
    "fonts",
    "help",
    "images",
    "img",
    "jobs",
    "js",
    "login",
    "mail",
    "media",
    "portal",
    "robots.txt",
    "sitemap",
    "sitemap.xml",
    "static",
    "status",
    "support",
    "test",
    "www",
}

_SLUG_REGEX = re.compile(r"^[a-z0-9][a-z0-9_\.-]{1,63}$", re.IGNORECASE)

# Provider SURT prefix signatures
PROVIDER_SURT_PREFIXES = {
    "greenhouse": "io,greenhouse,boards)/",
    "ashby": "com,ashbyhq,jobs)/",
    "lever": "co,lever,jobs)/",
    "breezy": "hr,breezy,",
    "recruitee": "com,recruitee,",
    "teamtailor": "com,teamtailor,",
}


def extract_token_from_surt(surt_line: str, provider: str) -> Optional[str]:
    """Extract a company slug token from a Common Crawl CDX/SURT line."""
    if not surt_line or not surt_line.strip():
        return None

    clean_line = surt_line.strip()
    surt_key = clean_line.split()[0]  # First column is the SURT URI

    provider_lower = provider.lower()
    prefix = PROVIDER_SURT_PREFIXES.get(provider_lower)
    if not prefix or not surt_key.startswith(prefix):
        return None

    token: Optional[str] = None

    # Path-based providers: io,greenhouse,boards)/{token}/...
    if provider_lower in {"greenhouse", "ashby", "lever"}:
        remainder = surt_key[len(prefix):]
        parts = remainder.strip("/").split("/")
        if parts and parts[0]:
            token = parts[0].strip().lower()

    # Subdomain-based providers: hr,breezy,{token})/
    elif provider_lower in {"breezy", "recruitee", "teamtailor"}:
        remainder = surt_key[len(prefix):]
        # format is {token})/ or {token})/path
        sub_parts = remainder.split(")/", 1)
        if sub_parts and sub_parts[0]:
            token = sub_parts[0].strip().lower()

    if not token or token in RESERVED_TOKENS:
        return None

    if not _SLUG_REGEX.match(token):
        return None

    return token


def build_provider_endpoint(provider: str, token: str) -> str:
    """Build the exact unauthenticated public API endpoint URL for a given provider and token."""
    prov = provider.lower().strip()
    tok = token.strip()

    if prov == "greenhouse":
        return f"https://boards-api.greenhouse.io/v1/boards/{tok}/jobs?content=true"
    if prov == "ashby":
        return f"https://api.ashbyhq.com/posting-api/job-board/{tok}?includeCompensation=true"
    if prov == "lever":
        return f"https://api.lever.co/v0/postings/{tok}?mode=json"
    if prov == "breezy":
        return f"https://{tok}.breezy.hr/json"
    if prov == "recruitee":
        return f"https://{tok}.recruitee.com/api/offers/"
    if prov == "teamtailor":
        return f"https://{tok}.teamtailor.com/jobs.json"

    raise ValueError(f"Unknown ATS provider: {provider}")


def extract_tokens_from_cdx_lines(lines: Iterable[str], provider: str) -> set[str]:
    """Extract and deduplicate company tokens from an iterable of CDX index lines."""
    tokens: set[str] = set()
    for line in lines:
        tok = extract_token_from_surt(line, provider)
        if tok:
            tokens.add(tok)

    logger.debug("extracted %d unique tokens for provider=%s", len(tokens), provider)
    return tokens
