import json
from pathlib import Path
import unittest

from jevscout.feeds.recruitee import parse_recruitee_feed


class RecruiteeFeedTests(unittest.TestCase):
    def setUp(self):
        fixture_path = Path(__file__).parent / "fixtures" / "feeds" / "recruitee_sample.json"
        self.payload = fixture_path.read_text(encoding="utf-8")
        self.source_url = "https://techco.recruitee.com/api/offers/"
        self.artifact_ref = "artifacts/pages/recruitee_sample.json"

    def test_extracts_all_jobs_when_india_filter_is_false(self):
        jobs = parse_recruitee_feed(
            self.payload,
            source_url=self.source_url,
            artifact_ref=self.artifact_ref,
            india_only=False,
        )
        self.assertEqual(len(jobs), 5)
        titles = [j["title"] for j in jobs]
        self.assertIn("Principal Architect, Distributed Data", titles)
        self.assertIn("Amsterdam Product Manager", titles)

    def test_extracts_strictly_india_jobs_when_india_only_is_true(self):
        jobs = parse_recruitee_feed(
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
                "Principal Architect, Distributed Data",
                "Senior Mobile Engineer (Android/iOS)",
                "AI Research Engineer (Global)",
            ],
        )

        first = jobs[0]
        self.assertEqual(first["title"], "Principal Architect, Distributed Data")
        self.assertEqual(first["location"], "Bengaluru, Karnataka, India")
        self.assertEqual(first["location_normalized"], "Bengaluru, Karnataka, India")
        self.assertTrue(first["is_india"])
        self.assertEqual(first["application_url"], "https://techco.recruitee.com/o/principal-architect")
        self.assertEqual(first["source_url"], self.source_url)
        self.assertEqual(first["artifact_ref"], self.artifact_ref)
        self.assertEqual(first["parser_version"], "feed-recruitee-v1")
        self.assertEqual(first["schema_version"], 1)

    def test_handles_malformed_json_safely(self):
        jobs = parse_recruitee_feed(
            "not a json object",
            source_url=self.source_url,
            artifact_ref=self.artifact_ref,
            india_only=True,
        )
        self.assertEqual(jobs, [])

    def test_handles_empty_offers_list(self):
        jobs = parse_recruitee_feed(
            json.dumps({"offers": []}),
            source_url=self.source_url,
            artifact_ref=self.artifact_ref,
            india_only=True,
        )
        self.assertEqual(jobs, [])
