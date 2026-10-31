"""Decision-model assessment of a saved job against private candidate context."""
from __future__ import annotations
import json

DIMENSIONS = {
    'qualification': 'Does the candidate have relevant skills and experience for this job?',
    'career_direction': 'Does the role align with the candidate’s stated career goals and desired work?',
    'ai_work': 'Does the role involve substantial AI, LLM, or machine learning engineering?',
    'backend_work': 'Does the role involve substantial backend, data pipelines, or systems engineering?',
    'location_fit': 'Does the job location or remote policy align with candidate preferences? Treat unspecified information as unknown.',
}

def classify_job(job, profile, client):
    context = str(profile.get('freeform_context') or '')[:12000]
    structured = profile.get('structured_fields') or {}
    state = ('Candidate context:\n' + context + '\nCandidate preferences:\n' +
             json.dumps(structured, ensure_ascii=False) + '\nJob:\n' +
             json.dumps({key: job.get(key) for key in ('title', 'location', 'description', 'application_url')}, ensure_ascii=False)[:12000])
    questions = {name: {'type': 'noul', 'instructions': text + ' Base the answer on provided evidence; do not invent missing facts.',
                        'criteria': {'true': 'Evidence supports this', 'false': 'Evidence does not support this'}}
                 for name, text in DIMENSIONS.items()}
    answers = client.evaluate(state, questions)
    dimensions = {}
    for name in questions:
        answer = answers.get(name)
        value = getattr(answer, 'noul', None)
        if isinstance(value, (float, int)) and 0 <= value <= 1:
            dimensions[name] = value
        else:
            dimensions[name] = None
    return {'model': client.model, 'dimensions': dimensions}
