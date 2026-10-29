from pathlib import Path
import unittest

from jevscout.feeds.registry import detect_feed_type, detect_and_parse_feed


class FeedRegistryTests(unittest.TestCase):
    def setUp(self):
        fixtures_dir = Path(__file__).parent / "fixtures" / "feeds"
        self.gh_payload = (fixtures_dir / "greenhouse_sample.json").read_text(encoding="utf-8")
        self.lever_payload = (fixtures_dir / "lever_sample.json").read_text(encoding="utf-8")
        self.ashby_payload = (fixtures_dir / "ashby_sample.json").read_text(encoding="utf-8")

    def test_detects_feed_type_from_urls(self):
        self.assertEqual(
            detect_feed_type("{}", "https://boards-api.greenhouse.io/v1/boards/stripe/jobs"),
            "greenhouse",
        )
        self.assertEqual(
            detect_feed_type("{}", "https://boards.greenhouse.io/stripe"),
            "greenhouse",
        )
        self.assertEqual(
            detect_feed_type("[]", "https://api.lever.co/v0/postings/postman?mode=json"),
            "lever",
        )
        self.assertEqual(
            detect_feed_type("[]", "https://jobs.lever.co/postman"),
            "lever",
        )
        self.assertEqual(
            detect_feed_type("{}", "https://api.ashbyhq.com/posting-api/job-board/retool"),
            "ashby",
        )
        self.assertEqual(
            detect_feed_type("{}", "https://jobs.ashbyhq.com/retool"),
            "ashby",
        )

    def test_detects_feed_type_from_payload_heuristics(self):
        self.assertEqual(detect_feed_type(self.gh_payload, "https://example.com/feed"), "greenhouse")
        self.assertEqual(detect_feed_type(self.lever_payload, "https://example.com/feed"), "lever")
        self.assertEqual(detect_feed_type(self.ashby_payload, "https://example.com/feed"), "ashby")

    def test_unified_parse_dispatches_properly_for_all_three(self):
        # Greenhouse
        gh_jobs = detect_and_parse_feed(
            self.gh_payload,
            source_url="https://boards-api.greenhouse.io/v1/boards/techcorp/jobs",
            artifact_ref="pages/gh.json",
            india_only=True,
        )
        self.assertEqual(len(gh_jobs), 3)
        self.assertEqual(gh_jobs[0]["parser_version"], "feed-greenhouse-v1")

        # Lever
        lever_jobs = detect_and_parse_feed(
            self.lever_payload,
            source_url="https://api.lever.co/v0/postings/postmanco?mode=json",
            artifact_ref="pages/lever.json",
            india_only=True,
        )
        self.assertEqual(len(lever_jobs), 3)
        self.assertEqual(lever_jobs[0]["parser_version"], "feed-lever-v1")

        # Ashby
        ashby_jobs = detect_and_parse_feed(
            self.ashby_payload,
            source_url="https://api.ashbyhq.com/posting-api/job-board/modernai",
            artifact_ref="pages/ashby.json",
            india_only=True,
        )
        self.assertEqual(len(ashby_jobs), 3)
        self.assertEqual(ashby_jobs[0]["parser_version"], "feed-ashby-v1")

    def test_unknown_feed_returns_empty_list(self):
        jobs = detect_and_parse_feed(
            '{"unrelated": true}',
            source_url="https://example.com/unknown",
            artifact_ref="pages/unknown.json",
            india_only=True,
        )
        self.assertEqual(jobs, [])
