"""HTTP contract tests for local per-user job decisions."""

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

if importlib.util.find_spec("fastapi") is None:
    raise unittest.SkipTest("FastAPI is not installed in this environment")

from fastapi.testclient import TestClient

from jevscout.interfaces.api import create_app
from jevscout.storage.filesystem import FileRunStore


class JobActionsApiTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.store = FileRunStore(self.root)
        self.assets = self.root / "user-assets"
        self.client = TestClient(create_app(store=self.store, pipeline_manager=object()))

    def tearDown(self):
        self.temporary.cleanup()

    def test_updates_are_per_user_persisted_and_unset_removes(self):
        url = "https://jobs.example/role/1?source=board#apply"
        self.assertEqual(self.client.get("/api/profile/alice/job-actions").json(), {})
        first = self.client.put("/api/profile/alice/job-actions", json={
            "job_url": url, "status": "interested",
        })
        self.assertEqual(first.status_code, 200)
        expected = {url: "interested"}
        self.assertEqual(first.json(), expected)
        self.assertEqual(self.client.get("/api/profile/alice/job-actions").json(), expected)

        other = self.client.put("/api/profile/bob/job-actions", json={
            "job_url": url, "status": "not_interested",
        })
        self.assertEqual(other.status_code, 200)
        self.assertEqual(self.client.get("/api/profile/alice/job-actions").json(), expected)

        cleared = self.client.put("/api/profile/alice/job-actions", json={
            "job_url": url, "status": "unset",
        })
        self.assertEqual(cleared.status_code, 200)
        self.assertEqual(cleared.json(), {})
        file_path = self.assets / "alice" / "job-actions.json"
        self.assertEqual(json.loads(file_path.read_text(encoding="utf-8")), {})

    def test_rejects_unsafe_usernames_urls_and_payload_fields(self):
        for username in ("../outside", "a/b", "bad name"):
            response = self.client.get(f"/api/profile/{username}/job-actions")
            self.assertNotEqual(response.status_code, 200)
        for url in (
            "javascript:alert(1)", "file:///etc/passwd", "//jobs.example/role",
            "https://user:password@jobs.example/role", "https://jobs.example:99999/role",
            " https://jobs.example/role",
        ):
            response = self.client.put("/api/profile/alice/job-actions", json={
                "job_url": url, "status": "interested",
            })
            self.assertEqual(response.status_code, 422, url)
        response = self.client.put("/api/profile/alice/job-actions", json={
            "job_url": "https://jobs.example/role", "status": "maybe",
        })
        self.assertEqual(response.status_code, 422)
        response = self.client.put("/api/profile/alice/job-actions", json={
            "job_url": "https://jobs.example/role", "status": "interested", "path": "../x",
        })
        self.assertEqual(response.status_code, 422)

    def test_job_actions_do_not_modify_profile_file(self):
        profile = self.client.put("/api/profile/alice", json={
            "freeform_context": "Prefer small teams", "structured_fields": {},
        })
        self.assertEqual(profile.status_code, 200)
        profile_path = self.assets / "alice" / "profile.json"
        before = profile_path.read_bytes()
        self.client.put("/api/profile/alice/job-actions", json={
            "job_url": "https://jobs.example/role", "status": "interested",
        })
        self.assertEqual(profile_path.read_bytes(), before)
        self.assertTrue((self.assets / "alice" / "job-actions.json").is_file())


if __name__ == "__main__":
    unittest.main()
