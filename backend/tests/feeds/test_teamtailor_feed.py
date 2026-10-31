import json
from pathlib import Path
import unittest

from jevscout.adapters.sources.teamtailor import parse_teamtailor_feed


class TeamtailorFeedTests(unittest.TestCase):
    def setUp(self):
        fixture_path = Path(__file__).resolve().parents[1] / "fixtures" / "feeds" / "teamtailor_sample.json"
        self.payload = fixture_path.read_text(encoding="utf-8")
        self.source_url = "https://brand.teamtailor.com/jobs.json"
        self.artifact_ref = "artifacts/pages/teamtailor_sample.json"

    def test_extracts_all_jobs_when_india_filter_is_false(self):
        jobs = parse_teamtailor_feed(
            self.payload,
            source_url=self.source_url,
            artifact_ref=self.artifact_ref,
            india_only=False,
        )
        self.assertEqual(len(jobs), 5)
        titles = [j["title"] for j in jobs]
        self.assertIn("Principal Infrastructure Architect", titles)
        self.assertIn("Stockholm Product Lead", titles)

    def test_extracts_strictly_india_jobs_when_india_only_is_true(self):
        jobs = parse_teamtailor_feed(
            self.payload,
            source_url=self.source_url,
            artifact_ref=self.artifact_ref,
            india_only=True,
        )
        self.assertEqual(len(jobs), 3)
        titles = [j["title"] for j in jobs]
        self.assertEqual(
            titles,
            [
                "Principal Infrastructure Architect",
                "Senior QA Automation Engineer",
                "Site Reliability Engineer (Global)",
            ],
        )

        first = jobs[0]
        self.assertEqual(first["title"], "Principal Infrastructure Architect")
        self.assertEqual(first["location"], "Bengaluru, Karnataka, India")
        self.assertEqual(first["location_normalized"], "Bengaluru, Karnataka, India")
        self.assertTrue(first["is_india"])
        self.assertEqual(first["application_url"], "https://brand.teamtailor.com/jobs/301-principal-infra")
        self.assertEqual(first["source_url"], self.source_url)
        self.assertEqual(first["artifact_ref"], self.artifact_ref)
        self.assertEqual(first["parser_version"], "feed-teamtailor-v1")
        self.assertEqual(first["schema_version"], 1)

    def test_handles_malformed_json_safely(self):
        jobs = parse_teamtailor_feed(
            "not a json array",
            source_url=self.source_url,
            artifact_ref=self.artifact_ref,
            india_only=True,
        )
        self.assertEqual(jobs, [])

    def test_handles_empty_list(self):
        jobs = parse_teamtailor_feed(
            "[]",
            source_url=self.source_url,
            artifact_ref=self.artifact_ref,
            india_only=True,
        )
        self.assertEqual(jobs, [])
