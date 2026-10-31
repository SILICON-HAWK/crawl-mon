"""Conservative title-based selection of technical engineering jobs."""
import re

_EXCLUDED = re.compile(r'\b(sales|pre[ -]?sales|teacher|teaching|tutor|instructor|professor|lecturer|recruiter|recruiting|recruitment|account executive|business development)\b', re.I)
_TECHNICAL = re.compile(r'\b(software|python|java|golang|node\.?js|backend|back[ -]end|frontend|front[ -]end|full[ -]?stack|developer|devops|devsecops|sre|site reliability|data (?:engineer|scientist|science|architect)|platform engineer|cloud engineer|security engineer|cybersecurity|quality assurance|qa engineer|test engineer|automation engineer|solutions engineer|solution engineer|systems engineer|embedded engineer|computer vision|ml engineer|forward[ -]deployed)\b', re.I)

_AI_ROLE = re.compile(r'\b(?:ai|artificial intelligence|machine learning|llm)\b.*\b(?:engineer|developer|scientist|researcher|architect)\b|\b(?:engineer|developer|scientist|researcher|architect)\b.*\b(?:ai|artificial intelligence|machine learning|llm)\b', re.I)

def classify_job_category(job: dict) -> str:
    """Classify only from title evidence, leaving unclear jobs undetermined."""
    title = job.get('title')
    if not isinstance(title, str) or not title.strip():
        return 'undetermined'
    if _EXCLUDED.search(title):
        return 'non_technical'
    if _TECHNICAL.search(title) or _AI_ROLE.search(title):
        return 'technical'
    return 'undetermined'


def is_technical_job(job: dict) -> bool:
    return classify_job_category(job) == 'technical'
