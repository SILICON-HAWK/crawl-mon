import json
from pathlib import Path
import unittest

from jevscout.adapters.sources.ashby import parse_ashby_feed


class AshbyFeedTests(unittest.TestCase):
    def setUp(self):
        fixture_path = Path(__file__).resolve().parents[1] / "fixtures" / "feeds" / "ashby_sample.json"
        self.payload = fixture_path.read_text(encoding="utf-8")
        self.source_url = "https://api.ashbyhq.com/posting-api/job-board/modernai?includeCompensation=true"
        self.artifact_ref = "artifacts/pages/ashby_sample.json"

    def test_extracts_all_jobs_when_india_filter_is_false(self):
        jobs = parse_ashby_feed(
            self.payload,
            source_url=self.source_url,
            artifact_ref=self.artifact_ref,
            india_only=False,
        )
        self.assertEqual(len(jobs), 5)
        titles = [j["title"] for j in jobs]
        self.assertIn("Software Engineer, Core Systems", titles)
        self.assertIn("Enterprise Sales Director", titles)

    def test_extracts_strictly_india_jobs_when_india_only_is_true(self):
        jobs = parse_ashby_feed(
            self.payload,
            source_url=self.source_url,
            artifact_ref=self.artifact_ref,
            india_only=True,
        )
        # 101 (Bengaluru), 102 (Worldwide Remote), 103 (Secondary location Bengaluru)
        self.assertEqual(len(jobs), 3)
        titles = [j["title"] for j in jobs]
        self.assertEqual(
            titles,
            [
                "Software Engineer, Core Systems",
                "Senior AI Infrastructure Engineer",
                "Full Stack Engineer (Global)",
            ],
        )

        first = jobs[0]
        self.assertEqual(first["title"], "Software Engineer, Core Systems")
        self.assertEqual(first["location"], "Bengaluru, India")
        self.assertEqual(first["location_normalized"], "Bengaluru, India")
        self.assertTrue(first["is_india"])
        self.assertEqual(first["application_url"], "https://jobs.ashbyhq.com/modernai/ashby-101")
        self.assertEqual(first["source_url"], self.source_url)
        self.assertEqual(first["artifact_ref"], self.artifact_ref)
        self.assertEqual(first["parser_version"], "feed-ashby-v1")
        self.assertEqual(first["schema_version"], 1)
        self.assertEqual(first["salary"], "₹35,00,000 - ₹55,00,000")
        self.assertEqual(jobs[2]["salary"], None)

    def test_handles_malformed_json_safely(self):
        jobs = parse_ashby_feed(
            "{broken json",
            source_url=self.source_url,
            artifact_ref=self.artifact_ref,
            india_only=True,
        )
        self.assertEqual(jobs, [])

    def test_handles_empty_jobs_array(self):
        jobs = parse_ashby_feed(
            json.dumps({"jobs": []}),
            source_url=self.source_url,
            artifact_ref=self.artifact_ref,
            india_only=True,
        )
        self.assertEqual(jobs, [])

    def test_company_is_null_without_explicit_employer(self):
        jobs = parse_ashby_feed(self.payload, self.source_url, self.artifact_ref, india_only=False)
        self.assertTrue(all(job["company"] is None for job in jobs))

    def test_extracts_explicit_company_name(self):
        payload = json.loads(self.payload)
        payload["jobs"][0]["companyName"] = "Modern AI"
        jobs = parse_ashby_feed(json.dumps(payload), self.source_url, self.artifact_ref, india_only=False)
        self.assertEqual(jobs[0]["company"], "Modern AI")
