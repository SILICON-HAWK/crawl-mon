"""Conservative title-based selection of technical engineering jobs."""
import re

_EXCLUDED = re.compile(r'\b(sales|pre[ -]?sales|teacher|teaching|tutor|instructor|professor|lecturer|recruiter|recruiting|recruitment|account executive|business development)\b', re.I)
_TECHNICAL = re.compile(r'\b(software|python|java|golang|node\.?js|backend|back[ -]end|frontend|front[ -]end|full[ -]?stack|developer|devops|devsecops|sre|site reliability|data (?:engineer|scientist|science|architect)|platform engineer|cloud engineer|security engineer|cybersecurity|quality assurance|qa engineer|test engineer|automation engineer|solutions engineer|solution engineer|systems engineer|embedded engineer|computer vision|ml engineer|forward[ -]deployed)\b', re.I)

_AI_ROLE = re.compile(r'\b(?:ai|artificial intelligence|machine learning|llm)\b.*\b(?:engineer|developer|scientist|researcher|architect)\b|\b(?:engineer|developer|scientist|researcher|architect)\b.*\b(?:ai|artificial intelligence|machine learning|llm)\b', re.I)

def is_technical_job(job: dict) -> bool:
    title = job.get('title')
    return isinstance(title, str) and bool(_TECHNICAL.search(title) or _AI_ROLE.search(title)) and not _EXCLUDED.search(title)
