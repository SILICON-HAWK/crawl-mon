"""HTTP contract tests for the local API adapter."""

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


class FakePipelineManager:
    def __init__(self):
        self.pipelines = {}

    def start(self, *, seed_urls, profile):
        pipeline = {
            "id": "pipe-1",
            "status": "queued",
            "seed_urls": seed_urls,
            "total_sources": len(seed_urls),
        }
        self.pipelines[pipeline["id"]] = pipeline
        return pipeline

    def list(self):
        return list(self.pipelines.values())

    def get(self, pipeline_id):
        return self.pipelines[pipeline_id]


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.store = FileRunStore(Path(self.temporary.name))
        self.record = self.store.create(RunSpec(["https://example.test/jobs"]))
        self.store.save_results(self.record.id, [{"title": "Engineer"}])
        self.client = TestClient(
            create_app(store=self.store, pipeline_manager=FakePipelineManager())
        )

    def tearDown(self):
        self.temporary.cleanup()

    def test_lists_saved_runs_and_results(self):
        response = self.client.get("/api/runs")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["id"], self.record.id)
        results = self.client.get(f"/api/runs/{self.record.id}/results")
        self.assertEqual(results.status_code, 200)
        self.assertEqual(results.json(), [{"title": "Engineer"}])

    def test_missing_run_is_not_found(self):
        self.assertEqual(
            self.client.get("/api/runs/not-a-run/results").status_code, 404
        )

    def test_pipeline_post_starts_explicit_request_and_can_be_inspected(self):
        response = self.client.post(
            "/api/pipeline",
            json={
                "seed_urls": ["https://example.test/jobs"],
                "profile": {"role_target": "Engineer"},
            },
        )
        self.assertEqual(response.status_code, 202)
        pipeline_id = response.json()["id"]
        self.assertEqual(self.client.get("/api/pipeline").json()[0]["id"], pipeline_id)
        self.assertEqual(
            self.client.get(f"/api/pipeline/{pipeline_id}").json()["status"], "queued"
        )

    def test_rejects_unknown_request_fields(self):
        response = self.client.post(
            "/api/pipeline",
            json={
                "seed_urls": ["https://example.test/jobs"],
                "profile": {"role_target": "Engineer", "api_key": "secret"},
            },
        )
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
