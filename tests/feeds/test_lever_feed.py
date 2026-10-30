import json
from pathlib import Path
import unittest

from jevscout.feeds.lever import parse_lever_feed


class LeverFeedTests(unittest.TestCase):
    def setUp(self):
        fixture_path = Path(__file__).resolve().parents[1] / "fixtures" / "feeds" / "lever_sample.json"
        self.payload = fixture_path.read_text(encoding="utf-8")
        self.source_url = "https://api.lever.co/v0/postings/postmanco?mode=json"
        self.artifact_ref = "artifacts/pages/lever_sample.json"

    def test_extracts_all_jobs_when_india_filter_is_false(self):
        jobs = parse_lever_feed(
            self.payload,
            source_url=self.source_url,
            artifact_ref=self.artifact_ref,
            india_only=False,
        )
        self.assertEqual(len(jobs), 5)
        titles = [j["title"] for j in jobs]
        self.assertIn("Lead Site Reliability Engineer", titles)
        self.assertIn("London Product Designer", titles)

    def test_extracts_strictly_india_jobs_when_india_only_is_true(self):
        jobs = parse_lever_feed(
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
                "Lead Site Reliability Engineer",
                "Staff Data Engineer",
                "Distributed Systems Engineer (India Remote)",
            ],
        )

        first = jobs[0]
        self.assertEqual(first["title"], "Lead Site Reliability Engineer")
        self.assertEqual(first["location"], "Bangalore")
        self.assertEqual(first["location_normalized"], "Bengaluru, India")
        self.assertTrue(first["is_india"])
        self.assertEqual(first["application_url"], "https://jobs.lever.co/postmanco/lever-101")
        self.assertEqual(first["source_url"], self.source_url)
        self.assertEqual(first["artifact_ref"], self.artifact_ref)
        self.assertEqual(first["parser_version"], "feed-lever-v1")
        self.assertEqual(first["schema_version"], 1)

    def test_handles_malformed_json_safely(self):
        jobs = parse_lever_feed(
            "not a json array",
            source_url=self.source_url,
            artifact_ref=self.artifact_ref,
            india_only=True,
        )
        self.assertEqual(jobs, [])

    def test_handles_empty_list(self):
        jobs = parse_lever_feed(
            "[]",
            source_url=self.source_url,
            artifact_ref=self.artifact_ref,
            india_only=True,
        )
        self.assertEqual(jobs, [])
