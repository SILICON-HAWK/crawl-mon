from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union


@dataclass(frozen=True)
class NoulAnswer:
    type: str  # "noul"
    noul: float  # probability [0.0 - 1.0]


@dataclass(frozen=True)
class ChoiceAnswer:
    type: str  # "choice"
    choice: str  # winning choice
    probabilities: Dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class ScoreAnswer:
    type: str  # "score"
    score: float  # ordinal rubric score
    probabilities: List[float] = field(default_factory=list)


DecisionAnswer = Union[NoulAnswer, ChoiceAnswer, ScoreAnswer]


class RecommendationTier(str, Enum):
    STRONG_MATCH = "STRONG_MATCH"
    REVIEW = "REVIEW"
    PASS = "PASS"


@dataclass(frozen=True)
class CandidateProfile:
    role_target: str
    primary_skills: List[str]
    experience_years: float
    preferred_locations: List[str]
    remote_only: bool = False
    secondary_skills: List[str] = field(default_factory=list)
    min_salary_inr: Optional[float] = None


@dataclass(frozen=True)
class JobPosting:
    title: str
    location: str
    url: str = ""
    company: Optional[str] = None
    description_snippet: Optional[str] = None
    source_platform: Optional[str] = None



@dataclass(frozen=True)
class JobMatchEvaluation:
    job_id: str
    job_title: str
    composite_score: float  # 0.0 to 100.0
    recommendation: RecommendationTier
    dimension_answers: Dict[str, DecisionAnswer]
    model_name: str
    reasoning: Optional[str] = None
