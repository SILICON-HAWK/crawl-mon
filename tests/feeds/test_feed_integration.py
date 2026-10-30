from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest

from jevscout.application import extract_run
from jevscout.models import RunSpec
from jevscout.storage import FileRunStore
from jevscout.cli import main


class FeedIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.tmp.name)
        self.store = FileRunStore(self.data_dir)
        self.fixtures_dir = Path(__file__).resolve().parents[1] / "fixtures" / "feeds"

    def tearDown(self):
        self.tmp.cleanup()

    def test_extract_run_from_saved_feed_extracts_india_jobs_strictly(self):
        spec = RunSpec(
            seed_urls=["https://boards-api.greenhouse.io/v1/boards/techcorp/jobs"],
            max_pages=1,
            max_depth=0,
            timeout_seconds=30,
        )
        record = self.store.create(spec)
        run_id = record.id

        # Simulate saved feed artifact
        gh_json = (self.fixtures_dir / "greenhouse_sample.json").read_text(encoding="utf-8")
        self.store.save_page(
            run_id,
            "https://boards-api.greenhouse.io/v1/boards/techcorp/jobs",
            gh_json,
            {"status_code": 200, "depth": 0},
        )
        self.store.update(replace(record, status="completed"))

        # Extract with india_only=True
        jobs = extract_run(self.store, run_id, india_only=True)

        self.assertEqual(len(jobs), 3)
        self.assertTrue(all(j.get("is_india") for j in jobs))
        titles = [j["title"] for j in jobs]
        self.assertIn("Staff Platform Engineer", titles)
        self.assertIn("Senior Backend Engineer", titles)
        self.assertIn("Frontend Architect", titles)
        self.assertNotIn("US Product Manager", titles)

        # Verify saved in store results
        saved = self.store.list_results(run_id)
        self.assertEqual(len(saved), 3)

    def test_cli_extract_and_results_with_india_only_flag(self):
        spec = RunSpec(
            seed_urls=["https://api.lever.co/v0/postings/postmanco?mode=json"],
            max_pages=1,
            max_depth=0,
            timeout_seconds=30,
        )
        record = self.store.create(spec)
        run_id = record.id

        lever_json = (self.fixtures_dir / "lever_sample.json").read_text(encoding="utf-8")
        self.store.save_page(
            run_id,
            "https://api.lever.co/v0/postings/postmanco?mode=json",
            lever_json,
            {"status_code": 200, "depth": 0},
        )
        self.store.update(replace(record, status="completed"))

        # Run extract without india_only (stores all 5)
        extract_run(self.store, run_id, india_only=False)
        self.assertEqual(len(self.store.list_results(run_id)), 5)

        # CLI results with --india-only should return only 3
        import io
        from contextlib import redirect_stdout

        out = io.StringIO()
        with redirect_stdout(out):
            code = main(["--data-dir", str(self.data_dir), "runs", "results", run_id, "--india-only"])
        self.assertEqual(code, 0)
        cli_results = json.loads(out.getvalue())
        self.assertEqual(len(cli_results), 3)
        self.assertTrue(all(j.get("is_india") for j in cli_results))

    def test_end_to_end_feed_extraction_to_decision_scoring(self):
        spec = RunSpec(
            seed_urls=["https://boards-api.greenhouse.io/v1/boards/techcorp/jobs"],
            max_pages=1,
            max_depth=0,
            timeout_seconds=30,
        )
        record = self.store.create(spec)
        run_id = record.id

        gh_json = (self.fixtures_dir / "greenhouse_sample.json").read_text(encoding="utf-8")
        self.store.save_page(
            run_id,
            "https://boards-api.greenhouse.io/v1/boards/techcorp/jobs",
            gh_json,
            {"status_code": 200, "depth": 0},
        )
        self.store.update(replace(record, status="completed"))

        # Extract India jobs
        extract_run(self.store, run_id, india_only=True)

        # Score run with candidate profile
        from jevscout.application import score_run
        from jevscout.scoring.client import LocalHeuristicDecisionClient
        from jevscout.scoring.models import CandidateProfile

        profile = CandidateProfile(
            role_target="Platform / Backend Engineer",
            primary_skills=["Distributed Systems", "Infrastructure"],
            experience_years=6.0,
            preferred_locations=["Bengaluru", "Pune"],
        )
        evaluations = score_run(
            self.store, run_id, profile, client=LocalHeuristicDecisionClient()
        )

        self.assertEqual(len(evaluations), 3)
        platform_eval = next(e for e in evaluations if "Platform" in e["job_title"])
        self.assertEqual(platform_eval["recommendation"], "STRONG_MATCH")

        # Verify stored evaluations
        stored = self.store.list_evaluations(run_id)
        self.assertEqual(len(stored), 3)
