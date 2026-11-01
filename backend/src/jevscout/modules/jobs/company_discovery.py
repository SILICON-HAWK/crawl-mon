"""Recognize official employer feed candidates from known ATS job URLs."""
import re
from urllib.parse import urlsplit

_TOKEN = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$')

def career_feed_candidate(url: object) -> str | None:
    if not isinstance(url, str): return None
    try:
        parts=urlsplit(url)
        if parts.scheme not in {'http','https'} or parts.username is not None or parts.password is not None or parts.port not in (None,443,80): return None
        host=(parts.hostname or '').lower(); segments=[x for x in parts.path.split('/') if x]
    except ValueError:
        return None
    if not segments or not _TOKEN.fullmatch(segments[0]): return None
    token=segments[0]
    if host in {'job-boards.greenhouse.io','boards.greenhouse.io'} and len(segments)>=3 and segments[1]=='jobs':
        return f'https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true'
    if host=='jobs.ashbyhq.com' and len(segments)>=2:
        return f'https://api.ashbyhq.com/posting-api/job-board/{token}?includeCompensation=true'
    if host=='jobs.lever.co' and len(segments)>=2:
        return f'https://api.lever.co/v0/postings/{token}?mode=json'
    return None
