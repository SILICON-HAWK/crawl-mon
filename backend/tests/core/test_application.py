"""Application failure handling at the external engine and saved-data boundaries."""

import asyncio
from pathlib import Path
import tempfile
import unittest

from jevscout.application.operations import execute_run, score_run
from jevscout.core.engine import PageEvidence
from jevscout.core.models import RunSpec
from jevscout.modules.jobs.scoring.client import LocalHeuristicDecisionClient
from jevscout.modules.jobs.scoring.models import CandidateProfile
from jevscout.storage.filesystem import FileRunStore


class ApplicationTests(unittest.IsolatedAsyncioTestCase):
    async def test_timeout_and_unusable_saved_metadata_still_leave_a_terminal_run(self):
        with tempfile.TemporaryDirectory() as directory:
            store = FileRunStore(Path(directory))
            run = store.create(RunSpec(["https://example.test/jobs"]))

            class TimedOutEngine:
                name = "timeout-fixture"
                version = "1"

                async def collect(self, spec, on_page, *, work_dir):
                    on_page(PageEvidence(spec.seed_urls[0], "<html>saved evidence</html>", 200, 0))
                    # Simulate unusable metadata at the filesystem boundary while
                    # a network timeout is being handled, not an internal mock.
                    store.save_page(run.id, "https://example.test/bad", "corrupted evidence",
                                    {"status_code": "invalid"})
                    raise asyncio.TimeoutError

            finished = await execute_run(store, run.id, approved=True, engine=TimedOutEngine())
            self.assertEqual(finished.status, "partial")
            self.assertEqual(store.get(run.id).status, "partial")
            self.assertEqual(store.read_execution(run.id)["error"],
                             "collection timed out; extraction failed")

    def test_score_run_evaluates_and_stores_results(self):
        with tempfile.TemporaryDirectory() as directory:
            store = FileRunStore(Path(directory))
            run = store.create(RunSpec(["https://example.test/jobs"]))
            jobs = [
                {
                    "title": "Senior Python Engineer",
                    "location": "Bengaluru, India",
                    "url": "https://example.test/job/1",
                    "company": "TechIndia",
                    "description": "FastAPI and PostgreSQL backend developer.",
                }
            ]
            store.save_results(run.id, jobs)

            profile = CandidateProfile(
                role_target="Senior Python Engineer",
                primary_skills=["Python", "FastAPI"],
                experience_years=5.0,
                preferred_locations=["Bengaluru"],
            )
            client = LocalHeuristicDecisionClient()
            evaluations = score_run(store, run.id, profile, client=client)

            self.assertEqual(len(evaluations), 1)
            self.assertEqual(evaluations[0]["recommendation"], "STRONG_MATCH")
            self.assertGreaterEqual(evaluations[0]["composite_score"], 75.0)

            stored = store.list_evaluations(run.id)
            self.assertEqual(len(stored), 1)
            self.assertEqual(stored[0]["job_title"], "Senior Python Engineer")

