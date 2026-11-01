import json
import unittest

from jevscout.adapters.sources.remoteok import parse_remoteok_feed


class RemoteOKFeedTests(unittest.TestCase):
    def setUp(self):
        self.source_url = "https://remoteok.com/api?tag=dev"
        self.artifact_ref = "artifacts/pages/remoteok_dev.json"
        self.payload = json.dumps(
            [
                {"legal": "terms"},
                {
                    "id": "123",
                    "position": "Senior Software Engineer",
                    "company": "Example Tech",
                    "location": "Bengaluru, India",
                    "date": "2026-10-31T00:00:04+00:00",
                    "url": "https://remoteok.com/remote-jobs/example-123",
                    "apply_url": "https://example.com/apply/123",
                    "salary_min": 100000,
                    "salary_max": 150000,
                    "description": "<p>Build software</p>",
                    "tags": ["dev", "python"],
                },
                {
                    "id": "456",
                    "position": "Platform Engineer",
                    "company": "Remote Example",
                    "location": "",
                    "epoch": 1793404804,
                    "url": "https://remoteok.com/remote-jobs/example-456",
                    "tags": ["dev"],
                },
            ]
        )

    def test_extracts_job_and_required_attribution(self):
        jobs = parse_remoteok_feed(
            self.payload, self.source_url, self.artifact_ref, india_only=True
        )
        self.assertEqual(len(jobs), 1)
        job = jobs[0]
        self.assertEqual(job["title"], "Senior Software Engineer")
        self.assertEqual(job["company"], "Example Tech")
        self.assertEqual(job["application_url"], "https://example.com/apply/123")
        self.assertEqual(
            job["original_job_url"],
            "https://remoteok.com/remote-jobs/example-123",
        )
        self.assertEqual(job["source_name"], "Remote OK")
        self.assertEqual(job["source_link"], "https://remoteok.com/?ref=jevscout")
        self.assertEqual(job["source_url"], self.source_url)
        self.assertEqual(job["artifact_ref"], self.artifact_ref)
        self.assertEqual(job["parser_version"], "feed-remoteok-v1")
        self.assertTrue(job["is_india"])

    def test_unknown_location_is_not_treated_as_india(self):
        jobs = parse_remoteok_feed(
            self.payload, self.source_url, self.artifact_ref, india_only=False
        )
        self.assertEqual(len(jobs), 2)
        self.assertIsNone(jobs[1]["location"])
        self.assertIsNone(jobs[1]["location_normalized"])
        self.assertFalse(jobs[1]["is_india"])
        self.assertEqual(jobs[1]["date_posted"], "2026-10-31T00:00:04+00:00")

    def test_rejects_malformed_or_wrong_shape_payload(self):
        self.assertEqual(
            parse_remoteok_feed("{bad", self.source_url, self.artifact_ref), []
        )
        self.assertEqual(
            parse_remoteok_feed("{}", self.source_url, self.artifact_ref), []
        )


if __name__ == "__main__":
    unittest.main()

class RemoteOkRegistryTests(unittest.TestCase):
    def test_registry_routes_only_remoteok_feed_host(self):
        from jevscout.adapters.sources.registry import detect_feed_type
        self.assertEqual(detect_feed_type('[]','https://remoteok.com/api?tag=dev'), 'remoteok')
        self.assertIsNone(detect_feed_type('[]','https://remoteok.com.attacker.test/api'))
