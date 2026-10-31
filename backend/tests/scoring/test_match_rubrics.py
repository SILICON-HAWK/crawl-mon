from __future__ import annotations

import unittest

from jevscout.scoring.models import CandidateProfile, JobPosting
from jevscout.scoring.rubrics import build_job_state, build_matching_questions


class MatchRubricsTests(unittest.TestCase):
    def setUp(self):
        self.profile = CandidateProfile(
            role_target="Senior Backend Engineer",
            primary_skills=["Python", "PostgreSQL", "FastAPI", "Docker"],
            experience_years=5.0,
            preferred_locations=["Bengaluru", "Remote (India)"],
            remote_only=False,
            secondary_skills=["Kubernetes", "Redis"],
        )
        self.job = JobPosting(
            title="Senior Python Backend Developer",
            location="Bengaluru, Karnataka, India",
            url="https://jobs.example.com/p/123",
            company="TechCorp India",
            description_snippet="We are looking for a Senior Python Developer with 4+ years experience in FastAPI, Docker, and relational databases.",
            source_platform="greenhouse",
        )

    def test_build_job_state_formats_candidate_and_job(self):
        state = build_job_state(self.profile, self.job)
        self.assertIn("candidate", state)
        self.assertIn("job", state)
        
        self.assertEqual(state["candidate"]["role_target"], "Senior Backend Engineer")
        self.assertEqual(state["candidate"]["experience_years"], 5.0)
        self.assertIn("FastAPI", state["candidate"]["primary_skills"])
        
        self.assertEqual(state["job"]["title"], "Senior Python Backend Developer")
        self.assertEqual(state["job"]["location"], "Bengaluru, Karnataka, India")
        self.assertEqual(state["job"]["company"], "TechCorp India")

    def test_build_matching_questions_generates_typed_decision_questions(self):
        questions = build_matching_questions(self.profile)
        
        # 1. Location / Remote compatibility (noul)
        self.assertIn("location_compatibility", questions)
        loc_q = questions["location_compatibility"]
        self.assertEqual(loc_q["type"], "noul")
        self.assertIn("instructions", loc_q)
        self.assertIn("criteria", loc_q)
        self.assertIn("Bengaluru", loc_q["instructions"])

        # 2. Seniority fit (choice)
        self.assertIn("seniority_fit", questions)
        sen_q = questions["seniority_fit"]
        self.assertEqual(sen_q["type"], "choice")
        self.assertIn("underqualified", sen_q["criteria"])
        self.assertIn("matched", sen_q["criteria"])
        self.assertIn("overqualified", sen_q["criteria"])

        # 3. Stack alignment (score)
        self.assertIn("stack_alignment", questions)
        stack_q = questions["stack_alignment"]
        self.assertEqual(stack_q["type"], "score")
        self.assertIsInstance(stack_q["criteria"], list)
        self.assertEqual(len(stack_q["criteria"]), 3)

    def test_remote_only_profile_adjusts_location_instructions(self):
        remote_profile = CandidateProfile(
            role_target="Engineer",
            primary_skills=["Python"],
            experience_years=2.0,
            preferred_locations=["Anywhere"],
            remote_only=True,
        )
        questions = build_matching_questions(remote_profile)
        loc_q = questions["location_compatibility"]
        self.assertIn("strictly remote", loc_q["instructions"].lower())
