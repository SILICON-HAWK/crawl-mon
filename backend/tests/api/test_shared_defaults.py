"""The development and built APIs see the same saved local data by default."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from jevscout.core.models import RunSpec
from jevscout.interfaces.api import create_app
from jevscout.storage.filesystem import FileRunStore


class SharedDefaultsTests(unittest.TestCase):
    def test_explicit_data_directory_is_respected(self):
        with tempfile.TemporaryDirectory() as directory:
            store = FileRunStore(Path(directory))
            run = store.create(RunSpec(["https://example.com/jobs"]))
            store.save_results(run.id, [{"title": "Backend Engineer"}])
            with patch.dict(os.environ, {"JEVSCOUT_DATA_DIR": directory}):
                client = TestClient(create_app(pipeline_manager=object()))
                self.assertEqual(client.get("/api/jobs").json()[0]["title"], "Backend Engineer")

    def test_default_and_built_configuration_read_same_jobs_and_profile(self):
        with tempfile.TemporaryDirectory() as directory:
            original = Path.cwd()
            try:
                os.chdir(directory)
                store = FileRunStore(Path("data/live-trial"))
                run = store.create(RunSpec(["https://example.com/jobs"]))
                store.save_results(run.id, [{"title": "AI Engineer"}])
                with patch.dict(os.environ, {}, clear=True):
                    dev = TestClient(create_app(pipeline_manager=object()))
                    dev.put("/api/profile/alice", json={"freeform_context": "Python", "structured_fields": {}}).raise_for_status()
                    with patch.dict(os.environ, {"JEVSCOUT_DATA_DIR": "data/live-trial"}):
                        built = TestClient(create_app(pipeline_manager=object()))
                    self.assertEqual(dev.get("/api/jobs").json(), built.get("/api/jobs").json())
                    self.assertEqual(dev.get("/api/jobs").json()[0]["title"], "AI Engineer")
                    self.assertEqual(built.get("/api/profile/alice").json()["freeform_context"], "Python")
            finally:
                os.chdir(original)
