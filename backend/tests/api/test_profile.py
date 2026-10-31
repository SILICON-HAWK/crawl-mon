"""HTTP contract tests for local profile storage."""

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


class ProfileApiTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        self.store = FileRunStore(root)
        self.assets = root / "user-assets"
        self.client = TestClient(create_app(store=self.store, pipeline_manager=object()))

    def tearDown(self):
        self.temporary.cleanup()

    def test_get_default_and_put_profile(self):
        default = self.client.get("/api/profile/alice")
        self.assertEqual(default.status_code, 200)
        self.assertEqual(default.json()["username"], "alice")
        payload = {
            "freeform_context": "Prefer small teams",
            "structured_fields": {
                "role_target": "Backend Engineer",
                "primary_skills": ["Python", "SQL"],
                "experience_years": 5,
                "preferred_locations": ["Remote", "Bengaluru"],
                "remote_only": True,
                "secondary_skills": ["AWS"],
                "min_salary_inr": 2000000,
            },
        }
        saved = self.client.put("/api/profile/alice", json=payload)
        self.assertEqual(saved.status_code, 200)
        self.assertEqual(saved.json()["freeform_context"], payload["freeform_context"])
        self.assertEqual(saved.json()["structured_fields"], payload["structured_fields"])
        self.assertEqual(self.client.get("/api/profile/alice").json(), saved.json())
        self.assertTrue((self.assets / "alice" / "files").is_dir())
        persisted = json.loads((self.assets / "alice" / "profile.json").read_text())
        self.assertEqual(persisted, saved.json())

    def test_rejects_invalid_usernames_and_unknown_fields(self):
        for username in ("../outside", "a/b", ".", "", "bad name"):
            self.assertNotEqual(self.client.get(f"/api/profile/{username}").status_code, 200)
        response = self.client.put(
            "/api/profile/alice",
            json={"freeform_context": "", "structured_fields": {}, "path": "../../secret"},
        )
        self.assertEqual(response.status_code, 422)

    def test_does_not_serve_user_files(self):
        user_files = self.assets / "alice" / "files"
        user_files.mkdir(parents=True)
        (user_files / "secret.txt").write_text("private")
        response = self.client.get("/api/profile/alice/files/secret.txt")
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
