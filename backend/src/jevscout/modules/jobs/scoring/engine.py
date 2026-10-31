from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from jevscout.modules.jobs.scoring.client import DecisionClient
from jevscout.modules.jobs.scoring.models import (
    CandidateProfile,
    ChoiceAnswer,
    JobMatchEvaluation,
    JobPosting,
    NoulAnswer,
    RecommendationTier,
    ScoreAnswer,
)
from jevscout.modules.jobs.scoring.rubrics import build_job_state, build_matching_questions


class JobMatchEngine:
    """Evaluates extracted jobs against candidate profile using a decision client."""

    def __init__(
        self,
        client: DecisionClient,
        *,
        location_weight: float = 0.25,
        seniority_weight: float = 0.35,
        stack_weight: float = 0.40,
        strong_threshold: float = 75.0,
        review_threshold: float = 50.0,
        min_location_pass: float = 0.40,
    ) -> None:
        self.client = client
        self.location_weight = location_weight
        self.seniority_weight = seniority_weight
        self.stack_weight = stack_weight
        self.strong_threshold = strong_threshold
        self.review_threshold = review_threshold
        self.min_location_pass = min_location_pass

    def _normalize_seniority(self, answer: ChoiceAnswer) -> float:
        choice = answer.choice.lower()
        if choice == "matched":
            return 1.0
        if choice == "overqualified":
            return 0.6
        if choice == "underqualified":
            return 0.15
        return 0.5  # Unknown / unlisted

    def _normalize_stack(self, answer: ScoreAnswer) -> float:
        # Score on a 0-2 scale: 0 -> 0.0, 1 -> 0.5, 2 -> 1.0
        score = answer.score
        if score <= 0.0:
            return 0.0
        if score >= 2.0:
            return 1.0
        return score / 2.0

    def evaluate_job(
        self,
        profile: CandidateProfile,
        job: Union[JobPosting, Dict[str, Any]],
        *,
        model: Optional[str] = None,
    ) -> JobMatchEvaluation:
        state = build_job_state(profile, job)
        questions = build_matching_questions(profile)

        answers = self.client.evaluate(state, questions, model=model)

        # Extract normalized scores for each dimension [0.0 - 1.0]
        loc_ans = answers.get("location_compatibility")
        loc_score = loc_ans.noul if isinstance(loc_ans, NoulAnswer) else 0.5

        sen_ans = answers.get("seniority_fit")
        sen_score = self._normalize_seniority(sen_ans) if isinstance(sen_ans, ChoiceAnswer) else 0.5

        stack_ans = answers.get("stack_alignment")
        stack_score = self._normalize_stack(stack_ans) if isinstance(stack_ans, ScoreAnswer) else 0.5

        # Weighted composite score on a scale of 0 to 100
        raw_composite = (
            (loc_score * self.location_weight)
            + (sen_score * self.seniority_weight)
            + (stack_score * self.stack_weight)
        )
        composite_score = round(raw_composite * 100.0, 1)

        # Determine recommendation tier
        if loc_score < self.min_location_pass:
            recommendation = RecommendationTier.PASS
        elif composite_score >= self.strong_threshold and loc_score >= 0.5:
            recommendation = RecommendationTier.STRONG_MATCH
        elif composite_score >= self.review_threshold:
            recommendation = RecommendationTier.REVIEW
        else:
            recommendation = RecommendationTier.PASS

        if isinstance(job, dict):
            job_id = (job.get("id") or job.get("url") or job.get("application_url")
                      or job.get("title", "unknown"))
        else:
            job_id = job.url or job.title
        job_title = job.get("title", "") if isinstance(job, dict) else job.title
        model_name = getattr(self.client, "model", model or "unknown_model")

        return JobMatchEvaluation(
            job_id=job_id,
            job_title=job_title,
            composite_score=composite_score,
            recommendation=recommendation,
            dimension_answers=answers,
            model_name=model_name,
        )

    def evaluate_batch(
        self,
        profile: CandidateProfile,
        jobs: List[Union[JobPosting, Dict[str, Any]]],
        *,
        model: Optional[str] = None,
    ) -> List[JobMatchEvaluation]:
        return [self.evaluate_job(profile, job, model=model) for job in jobs]
