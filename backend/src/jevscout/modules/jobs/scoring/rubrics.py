from __future__ import annotations

from typing import Any, Dict, Union

from jevscout.modules.jobs.scoring.models import CandidateProfile, JobPosting


def build_job_state(
    profile: CandidateProfile,
    job: Union[JobPosting, Dict[str, Any]],
) -> Dict[str, Any]:
    """Serialize candidate profile and job posting into structured state for decisions."""
    if isinstance(job, dict):
        title = job.get("title", "")
        location = job.get("location", "")
        company = job.get("company")
        snippet = job.get("description") or job.get("description_snippet", "")
        source = job.get("source_platform") or job.get("parser_version", "")
    else:
        title = job.title
        location = job.location
        company = job.company
        snippet = job.description_snippet or ""
        source = job.source_platform or ""

    # Truncate overly long descriptions to prevent excessive token usage
    max_snippet_len = 1200
    cleaned_snippet = snippet[:max_snippet_len] if snippet else ""

    return {
        "candidate": {
            "role_target": profile.role_target,
            "primary_skills": profile.primary_skills,
            "secondary_skills": profile.secondary_skills,
            "experience_years": profile.experience_years,
            "preferred_locations": profile.preferred_locations,
            "remote_only": profile.remote_only,
        },
        "job": {
            "title": title,
            "company": company,
            "location": location,
            "description_summary": cleaned_snippet,
            "source": source,
        },
    }


def build_matching_questions(profile: CandidateProfile) -> Dict[str, Dict[str, Any]]:
    """Generate typed questions (noul, choice, score) tailored to the candidate profile."""
    locations_str = ", ".join(profile.preferred_locations)
    skills_str = ", ".join(profile.primary_skills)

    if profile.remote_only:
        loc_instructions = (
            "Is this position strictly remote eligible for a candidate residing in India? "
            "Candidate requires 100% remote work."
        )
        loc_criteria = {
            "true": "Position is explicitly fully remote in India or worldwide",
            "false": "Position requires onsite presence or relocation",
        }
    else:
        loc_instructions = (
            f"Is this job location compatible with candidate's preferred locations ({locations_str}) "
            "or eligible for remote work in India?"
        )
        loc_criteria = {
            "true": f"Located in {locations_str} or offers remote flexibility in India",
            "false": "In an unlisted location requiring mandatory onsite work",
        }

    return {
        "location_compatibility": {
            "type": "noul",
            "instructions": loc_instructions,
            "criteria": loc_criteria,
        },
        "seniority_fit": {
            "type": "choice",
            "instructions": (
                f"Candidate has {profile.experience_years} years experience targeting '{profile.role_target}'. "
                "How does the job's expected seniority level fit the candidate?"
            ),
            "criteria": {
                "underqualified": "Candidate lacks sufficient years, seniority, or mandatory prerequisites",
                "matched": f"Level aligns with ~{profile.experience_years} years experience and target role",
                "overqualified": "Candidate exceeds the level needed (e.g. entry/junior role)",
            },
        },
        "stack_alignment": {
            "type": "score",
            "instructions": (
                f"Evaluate alignment between candidate's core skills ({skills_str}) "
                "and the job's technical stack requirements."
            ),
            "criteria": [
                "Minimal or no overlap with core requirements",
                "Partial overlap with adjacent skills or secondary match",
                "Strong direct match with primary target stack",
            ],
        },
    }
