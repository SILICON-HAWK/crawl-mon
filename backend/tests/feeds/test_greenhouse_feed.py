import json
from pathlib import Path
import unittest

from jevscout.feeds.greenhouse import parse_greenhouse_feed


class GreenhouseFeedTests(unittest.TestCase):
    def setUp(self):
        fixture_path = Path(__file__).resolve().parents[1] / "fixtures" / "feeds" / "greenhouse_sample.json"
        self.payload = fixture_path.read_text(encoding="utf-8")
        self.source_url = "https://boards-api.greenhouse.io/v1/boards/techcorp/jobs?content=true"
        self.artifact_ref = "artifacts/pages/gh_sample.json"

    def test_extracts_all_jobs_when_india_filter_is_false(self):
        jobs = parse_greenhouse_feed(
            self.payload,
            source_url=self.source_url,
            artifact_ref=self.artifact_ref,
            india_only=False,
        )
        self.assertEqual(len(jobs), 5)
        titles = [j["title"] for j in jobs]
        self.assertIn("Staff Platform Engineer", titles)
        self.assertIn("US Product Manager", titles)

    def test_extracts_strictly_india_jobs_when_india_only_is_true(self):
        jobs = parse_greenhouse_feed(
            self.payload,
            source_url=self.source_url,
            artifact_ref=self.artifact_ref,
            india_only=True,
        )
        # Should only include Bengaluru, Pune, and India - Remote (3 out of 5)
        self.assertEqual(len(jobs), 3)
        titles = [j["title"] for j in jobs]
        self.assertEqual(
            titles,
            [
                "Staff Platform Engineer",
                "Senior Backend Engineer",
                "Frontend Architect",
            ],
        )

        first = jobs[0]
        self.assertEqual(first["title"], "Staff Platform Engineer")
        self.assertEqual(first["location"], "Bengaluru, Karnataka, India")
        self.assertEqual(first["location_normalized"], "Bengaluru, Karnataka, India")
        self.assertTrue(first["is_india"])
        self.assertEqual(first["application_url"], "https://boards.greenhouse.io/techcorp/jobs/101")
        self.assertEqual(first["source_url"], self.source_url)
        self.assertEqual(first["artifact_ref"], self.artifact_ref)
        self.assertEqual(first["parser_version"], "feed-greenhouse-v1")
        self.assertEqual(first["schema_version"], 1)

    def test_handles_malformed_json_safely(self):
        jobs = parse_greenhouse_feed(
            "{not valid json",
            source_url=self.source_url,
            artifact_ref=self.artifact_ref,
            india_only=True,
        )
        self.assertEqual(jobs, [])

    def test_handles_empty_or_missing_jobs_list(self):
        jobs = parse_greenhouse_feed(
            json.dumps({"jobs": []}),
            source_url=self.source_url,
            artifact_ref=self.artifact_ref,
            india_only=True,
        )
        self.assertEqual(jobs, [])
