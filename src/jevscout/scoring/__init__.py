"""Agnostic decision model scoring module."""
from __future__ import annotations

from jevscout.scoring.client import (
    DecisionClient,
    LocalHeuristicDecisionClient,
    OpenRouterDecisionClient,
)
from jevscout.scoring.engine import JobMatchEngine
from jevscout.scoring.models import (
    CandidateProfile,
    ChoiceAnswer,
    DecisionAnswer,
    JobMatchEvaluation,
    JobPosting,
    NoulAnswer,
    RecommendationTier,
    ScoreAnswer,
)
from jevscout.scoring.rubrics import build_job_state, build_matching_questions

__all__ = [
    "CandidateProfile",
    "ChoiceAnswer",
    "DecisionAnswer",
    "DecisionClient",
    "JobMatchEngine",
    "JobMatchEvaluation",
    "JobPosting",
    "LocalHeuristicDecisionClient",
    "NoulAnswer",
    "OpenRouterDecisionClient",
    "RecommendationTier",
    "ScoreAnswer",
    "build_job_state",
    "build_matching_questions",
]
