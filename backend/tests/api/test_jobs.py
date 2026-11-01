"""Contract tests for the aggregated saved jobs endpoint."""

import importlib.util
import tempfile
import unittest
from pathlib import Path

if importlib.util.find_spec("fastapi") is None:
    raise unittest.SkipTest("FastAPI is not installed in this environment")

from fastapi.testclient import TestClient

from jevscout.core.models import RunSpec
from jevscout.interfaces.api import create_app
from jevscout.storage.filesystem import FileRunStore


class JobsApiTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.store = FileRunStore(Path(self.temporary.name))
        self.client = TestClient(create_app(store=self.store, pipeline_manager=object()))

    def tearDown(self):
        self.temporary.cleanup()

    def test_aggregates_newest_first_with_raw_fields_and_original_provenance(self):
        older = self.store.create(RunSpec(["https://source.test/old"]))
        older.created_at = "2026-01-01T00:00:00Z"
        self.store.update(older)
        self.store.save_results(older.id, [
            {"title": "Engineer", "application_url": "https://jobs.test/role/1",
             "salary": {"min": 90000, "currency": "INR"}, "skills": ["Python"],
             "requirements": ["3 years"]},
            {"title": "Other", "application_url": None, "requirements": ["3 years"]},
        ])

        newer = self.store.create(RunSpec(["https://source.test/new"]))
        newer.created_at = "2026-02-01T00:00:00Z"
        self.store.update(newer)
        self.store.save_results(newer.id, [
            {"title": "Engineer", "application_url": "https://JOBS.test:443/role/1#apply",
             "salary": "₹10–12 LPA", "skills": ["Go"]},
        ])

        response = self.client.get("/api/jobs?technical_only=false")
        self.assertEqual(response.status_code, 200)
        jobs = response.json()
        self.assertEqual(jobs[0]["run_id"], newer.id)
        self.assertEqual(jobs[0]["job_index"], 0)
        self.assertEqual(jobs[0]["salary"], "₹10–12 LPA")
        self.assertEqual(jobs[0]["skills"], ["Go"])
        self.assertEqual(jobs[0]["originals"], [
            {"run_id": newer.id, "job_index": 0},
            {"run_id": older.id, "job_index": 0},
        ])
        self.assertEqual(jobs[1]["run_id"], older.id)
        self.assertEqual(jobs[1]["job_index"], 1)
        self.assertIsNone(jobs[1]["application_url"])
        self.assertEqual(jobs[1]["requirements"], ["3 years"])

    def test_default_filters_sales_and_teaching_but_keeps_engineering(self):
        run = self.store.create(RunSpec(["https://source.test/"]))
        self.store.save_results(run.id, [{"title": "AI Engineer"}, {"title": "Sales Manager"}, {"title": "Math Teacher"}, {"title": "Product Specialist"}])
        self.assertEqual([job["title"] for job in self.client.get("/api/jobs").json()], ["AI Engineer"])
        all_jobs = self.client.get("/api/jobs?technical_only=false").json()
        self.assertEqual(len(all_jobs), 4)
        self.assertEqual([job["job_category"] for job in all_jobs], ["technical", "non_technical", "non_technical", "undetermined"])


if __name__ == "__main__":
    unittest.main()


class JobsPreRankApiTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.store = FileRunStore(Path(self.temporary.name))
        self.client = TestClient(create_app(store=self.store, pipeline_manager=object()))
        run = self.store.create(RunSpec(["https://source.test/x"]))
        self.store.save_results(run.id, [
            {"title": "Forward Deployed AI Engineer", "location": "India",
             "application_url": "https://jobs.test/a"},
            {"title": "Software Engineer", "location": "Berlin, Germany",
             "application_url": "https://jobs.test/b"},
        ])

    def tearDown(self):
        self.temporary.cleanup()

    def test_pre_rank_attached_only_when_username_given(self):
        plain = self.client.get("/api/jobs").json()
        self.assertTrue(all("pre_rank" not in job for job in plain))
        self.client.put("/api/profile/tester", json={
            "freeform_context": "", "structured_fields": {
                "role_target": "AI Forward Deployed Engineer", "primary_skills": ["Python"],
                "experience_years": 2, "preferred_locations": ["India"], "remote_only": False}})
        ranked = self.client.get("/api/jobs", params={"username": "tester"}).json()
        by_url = {job["application_url"]: job["pre_rank"] for job in ranked}
        self.assertGreater(by_url["https://jobs.test/a"]["score"], by_url["https://jobs.test/b"]["score"])
        self.assertEqual(set(by_url["https://jobs.test/a"]), {"score", "title", "salary", "location", "reasons"})

    def test_invalid_username_is_rejected(self):
        self.assertEqual(self.client.get("/api/jobs", params={"username": "../x"}).status_code, 422)
