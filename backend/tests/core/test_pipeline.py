"""Tests for the bounded user-started collection pipeline."""

from dataclasses import replace
from pathlib import Path
import tempfile
import time
import unittest

from jevscout.application.pipeline import PipelineManager
from jevscout.core.engine import CollectionReport, PageEvidence
from jevscout.modules.jobs.scoring.models import CandidateProfile
from jevscout.storage.filesystem import FileRunStore


class FixtureEngine:
    name = "fixture"
    version = "1"

    async def collect(self, spec, on_page, *, work_dir):
        html = '''<script type="application/ld+json">{"@type":"JobPosting",
          "title":"Python Engineer","description":"Python FastAPI engineer",
          "hiringOrganization":{"name":"Example"},"jobLocation":{"address":
          {"addressLocality":"Toronto"}},"url":"https://jobs.test/1"}</script>'''
        on_page(PageEvidence(spec.seed_urls[0], html, 200, 0))
        return CollectionReport(pages_saved=1)


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = FileRunStore(Path(self.temp.name))
        self.profile = CandidateProfile("Python Engineer", ["Python", "FastAPI"], 5,
                                         ["Toronto"])

    def tearDown(self):
        self.temp.cleanup()

    def wait(self, manager, pipeline_id):
        for _ in range(200):
            state = manager.get(pipeline_id)
            if state["status"] not in {"queued", "running"}:
                return state
            time.sleep(0.01)
        self.fail("pipeline did not finish")

    def test_explicit_start_collects_and_ranks_with_provenance(self):
        manager = PipelineManager(self.store, FixtureEngine())
        started = manager.start(["https://jobs.test/careers"], self.profile)
        self.assertEqual(started["status"], "queued")
        done = self.wait(manager, started["id"])
        self.assertEqual(done["status"], "completed")
        self.assertEqual(done["runs"][0]["items_found"], 1)
        result = done["results"][0]
        self.assertEqual(result["title"], "Python Engineer")
        self.assertEqual(result["matched_skills"], ["Python", "FastAPI"])
        self.assertEqual(result["provenance"]["seed_url"], "https://jobs.test/careers")

    def test_limits_and_invalid_urls_are_rejected_before_start(self):
        manager = PipelineManager(self.store, FixtureEngine())
        with self.assertRaises(ValueError):
            manager.start(["https://a.test", "https://b.test", "https://c.test",
                           "https://d.test", "https://e.test", "https://f.test"], self.profile)
        with self.assertRaises(ValueError):
            manager.start(["file:///etc/passwd"], self.profile)
        with self.assertRaises(ValueError):
            manager.start([None], self.profile)
        with self.assertRaises(ValueError):
            manager.start(["https://jobs.test"], replace(self.profile, primary_skills=[""]))
        with self.assertRaises(ValueError):
            manager.start(["https://jobs.test"], replace(self.profile, experience_years=float("nan")))
        self.assertEqual(manager.list(), [])


if __name__ == "__main__":
    unittest.main()
