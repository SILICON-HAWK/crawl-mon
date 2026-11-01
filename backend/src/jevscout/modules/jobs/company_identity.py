"""Employer identities for specific, verified company-owned job feeds.

Mappings are explicit source configuration, not guesses from URL slugs.
"""
from urllib.parse import urlsplit

FEED_EMPLOYERS = {
    ('boards-api.greenhouse.io', '/v1/boards/sonicwall/jobs'): 'SonicWall',
    ('api.ashbyhq.com', '/posting-api/job-board/firstwork'): 'Firstwork',
    ('transperfect.recruitee.com', '/api/offers'): 'TransPerfect',
}

def resolve_company(job: dict) -> str | None:
    source = job.get('source_url')
    if isinstance(source, str):
        parts = urlsplit(source)
        configured = FEED_EMPLOYERS.get(((parts.hostname or '').lower(), parts.path.rstrip('/').lower()))
        if configured:
            return configured
    value = job.get('company')
    return value.strip() if isinstance(value, str) and value.strip() else None
