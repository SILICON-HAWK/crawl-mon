"""Real PostgreSQL contract tests; set JEVSCOUT_TEST_DATABASE_URL to run."""
import os
import json
import subprocess
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from jevscout.models import RunSpec
from jevscout.postgres import PostgresRunStore


DATABASE_URL = os.environ.get("JEVSCOUT_TEST_DATABASE_URL")
PROJECT_ROOT = Path(__file__).resolve().parents[2]


@unittest.skipUnless(DATABASE_URL, "requires JEVSCOUT_TEST_DATABASE_URL")
class PostgresRunStoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = tempfile.TemporaryDirectory()
        cls.store = PostgresRunStore(DATABASE_URL, Path(cls.root.name))
        cls.store.initialize_schema()

    @classmethod
    def tearDownClass(cls):
        cls.root.cleanup()

    def test_run_records_persist_across_instances(self):
        run = self.store.create(RunSpec(["https://example.test/jobs"]))
        reopened = PostgresRunStore(DATABASE_URL, Path(self.root.name))
        self.assertEqual(reopened.get(run.id), run)
        self.assertIn(run, reopened.list_runs())
        finished = replace(run, status="completed")
        reopened.update(finished)
        self.assertEqual(self.store.get(run.id), finished)

    def test_schema_initialization_is_idempotent(self):
        reopened = PostgresRunStore(DATABASE_URL, Path(self.root.name))
        reopened.initialize_schema()
        self.assertEqual(reopened.list_runs(), self.store.list_runs())

    def test_pages_and_artifacts_round_trip_atomically(self):
        run = self.store.create(RunSpec(["https://example.test/jobs"]))
        ref = self.store.save_page(run.id, "https://example.test/jobs", "<html>x</html>", {"code": 200})
        self.assertEqual(self.store.read_artifact(run.id, ref), "<html>x</html>")
        self.assertEqual(self.store.list_pages(run.id), [{"url": "https://example.test/jobs", "artifact_ref": ref, "metadata": {"code": 200}}])
        with self.assertRaises(ValueError):
            self.store.save_page(run.id, "https://example.test/jobs", "bad", {"n": float("nan")})
        self.assertEqual(len(self.store.list_pages(run.id)), 1)
        # PostgreSQL text rejects NUL bytes. A failed two-column write must
        # leave no orphan metadata, and the transaction must remain usable.
        with self.assertRaises(RuntimeError):
            self.store.save_page(run.id, "https://example.test/jobs", "bad\0html", {"code": 500})
        self.assertEqual(len(self.store.list_pages(run.id)), 1)
        later_ref = self.store.save_page(run.id, "https://example.test/jobs", "<html>later</html>", {"code": 201})
        self.assertEqual(self.store.read_artifact(run.id, later_ref), "<html>later</html>")

    def test_execution_results_and_evaluations_persist(self):
        run = self.store.create(RunSpec(["https://example.test/jobs"]))
        self.assertIsNone(self.store.read_execution(run.id))
        self.assertEqual(self.store.list_results(run.id), [])
        self.assertEqual(self.store.list_evaluations(run.id), [])
        self.store.write_execution(run.id, {"status": "completed"})
        self.store.save_results(run.id, [{"title": "Engineer"}])
        self.store.save_evaluations(run.id, [{"score": 8}])
        reopened = PostgresRunStore(DATABASE_URL, Path(self.root.name))
        self.assertEqual(reopened.read_execution(run.id), {"status": "completed"})
        self.assertEqual(reopened.list_results(run.id), [{"title": "Engineer"}])
        self.assertEqual(reopened.list_evaluations(run.id), [{"score": 8}])
        with self.assertRaises(ValueError):
            self.store.save_results(run.id, [{"score": float("nan")}])
        self.assertEqual(reopened.list_results(run.id), [{"title": "Engineer"}])

    def test_saved_evidence_extracts_and_scores_through_application(self):
        from jevscout.application import extract_run, score_run
        from jevscout.scoring.client import LocalHeuristicDecisionClient
        from jevscout.scoring.models import CandidateProfile

        run = self.store.create(RunSpec(["https://careers.example.test/openings"]))
        html = (PROJECT_ROOT / "tests" / "fixtures" / "jobs.html").read_text(encoding="utf-8")
        self.store.save_page(run.id, "https://careers.example.test/openings", html, {"status_code": 200})
        self.store.update(replace(run, status="completed"))
        extracted = extract_run(self.store, run.id)
        self.assertEqual([item["title"] for item in extracted], ["Platform Engineer", "Remote Product Designer"])
        evaluations = score_run(
            self.store,
            run.id,
            CandidateProfile("Platform Engineer", ["Python", "platform"], 8, ["Bengaluru", "Remote"]),
            client=LocalHeuristicDecisionClient(),
        )
        self.assertEqual(len(evaluations), 2)
        self.assertEqual(self.store.list_evaluations(run.id), evaluations)

    def test_cli_initializes_creates_and_reads_postgres_run(self):
        with tempfile.TemporaryDirectory() as directory:
            data_dir = Path(directory)
            env = os.environ.copy()
            env["PYTHONPATH"] = str(PROJECT_ROOT / "src")
            env["JEVSCOUT_DATABASE_URL"] = DATABASE_URL

            def invoke(*args):
                return subprocess.run(
                    [sys.executable, "-m", "jevscout", "--data-dir", str(data_dir), *args],
                    cwd=PROJECT_ROOT,
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=30,
                    check=False,
                )

            initialized = invoke("db", "init")
            self.assertEqual(initialized.returncode, 0, initialized.stderr)
            created = invoke("runs", "create", "--seed", "https://example.test/jobs")
            self.assertEqual(created.returncode, 0, created.stderr)
            record = json.loads(created.stdout)
            shown = invoke("runs", "show", record["id"])
            self.assertEqual(shown.returncode, 0, shown.stderr)
            self.assertEqual(json.loads(shown.stdout), record)

    def test_invalid_ids_refs_and_missing_runs_are_rejected(self):
        with self.assertRaises(ValueError):
            self.store.get("../bad")
        with self.assertRaises(ValueError):
            self.store.read_artifact("00000000-0000-0000-0000-000000000000", "../../bad")
        missing = "00000000-0000-0000-0000-000000000000"
        with self.assertRaises(FileNotFoundError):
            self.store.get(missing)
        with self.assertRaises(FileNotFoundError):
            self.store.write_execution(missing, {})

    def test_operation_lock_is_reentrant_per_instance_and_shared_between_instances(self):
        other_root = tempfile.TemporaryDirectory()
        self.addCleanup(other_root.cleanup)
        other = PostgresRunStore(DATABASE_URL, Path(other_root.name))
        with self.store.operation_lock():
            with self.store.operation_lock():
                with self.assertRaisesRegex(RuntimeError, "another operation"):
                    with other.operation_lock():
                        pass
        with other.operation_lock():
            pass


if __name__ == "__main__":
    unittest.main()
