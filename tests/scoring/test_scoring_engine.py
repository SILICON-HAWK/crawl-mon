from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from jevscout.scoring.client import DecisionClient
from jevscout.scoring.engine import JobMatchEngine
from jevscout.scoring.models import (
    CandidateProfile,
    ChoiceAnswer,
    JobMatchEvaluation,
    JobPosting,
    NoulAnswer,
    RecommendationTier,
    ScoreAnswer,
)


class ScoringEngineTests(unittest.TestCase):
    def setUp(self):
        self.profile = CandidateProfile(
            role_target="Staff Systems Engineer",
            primary_skills=["Go", "Kubernetes", "Linux"],
            experience_years=8.0,
            preferred_locations=["Bengaluru", "Remote"],
        )
        self.job = JobPosting(
            title="Principal Infrastructure Engineer",
            location="Bengaluru, India",
            url="https://example.com/job/1",
            company="CloudCorp",
            description_snippet="Looking for a high-scale Go and Kubernetes systems expert.",
        )

    def test_evaluate_job_strong_match(self):
        mock_client = MagicMock(spec=DecisionClient)
        mock_client.model = "respan/span-01-lite:free"
        mock_client.evaluate.return_value = {
            "location_compatibility": NoulAnswer(type="noul", noul=0.95),
            "seniority_fit": ChoiceAnswer(
                type="choice",
                choice="matched",
                probabilities={"underqualified": 0.05, "matched": 0.85, "overqualified": 0.10},
            ),
            "stack_alignment": ScoreAnswer(
                type="score",
                score=2.0,  # Max score on 0-2 scale
                probabilities=[0.05, 0.15, 0.80],
            ),
        }

        engine = JobMatchEngine(client=mock_client)
        result = engine.evaluate_job(self.profile, self.job)

        self.assertIsInstance(result, JobMatchEvaluation)
        self.assertEqual(result.recommendation, RecommendationTier.STRONG_MATCH)
        self.assertGreaterEqual(result.composite_score, 80.0)
        self.assertEqual(result.model_name, "respan/span-01-lite:free")

    def test_evaluate_job_pass_due_to_low_location(self):
        mock_client = MagicMock(spec=DecisionClient)
        mock_client.model = "respan/span-01-lite:free"
        mock_client.evaluate.return_value = {
            "location_compatibility": NoulAnswer(type="noul", noul=0.1),
            "seniority_fit": ChoiceAnswer(type="choice", choice="matched"),
            "stack_alignment": ScoreAnswer(type="score", score=2.0),
        }

        engine = JobMatchEngine(client=mock_client)
        result = engine.evaluate_job(self.profile, self.job)

        self.assertEqual(result.recommendation, RecommendationTier.PASS)

    def test_evaluate_batch_scores_multiple_jobs(self):
        mock_client = MagicMock(spec=DecisionClient)
        mock_client.model = "respan/span-01-lite:free"
        mock_client.evaluate.return_value = {
            "location_compatibility": NoulAnswer(type="noul", noul=0.8),
            "seniority_fit": ChoiceAnswer(type="choice", choice="matched"),
            "stack_alignment": ScoreAnswer(type="score", score=0.0),
        }

        engine = JobMatchEngine(client=mock_client)
        jobs = [
            self.job,
            JobPosting(title="Go Developer", location="Remote", company="StartUp"),
        ]
        results = engine.evaluate_batch(self.profile, jobs)

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].recommendation, RecommendationTier.REVIEW)
        self.assertEqual(results[0].composite_score, 55.0)
