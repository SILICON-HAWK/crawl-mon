"""End-to-end collection through real CLI processes and the real Crawlee engine."""

import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest

from fixture_site import fixture_site
from test_cli import invoke


@unittest.skipUnless(importlib.util.find_spec("crawlee"), "install .[crawl] for collection checks")
class CollectionCliTests(unittest.TestCase):
    def test_collect_saved_evidence_extract_and_replay_after_site_is_offline(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with fixture_site() as (origin, hits):
                created = invoke(root, "runs", "create", "--seed", origin + "/",
                                 "--allow-local", "--max-depth", "1", "--max-pages", "4")
                self.assertEqual(created.returncode, 0, created.stderr)
                run_id = json.loads(created.stdout)["id"]
                executed = invoke(root, "--debug", "runs", "execute", run_id, "--approve")
                self.assertEqual(executed.returncode, 0, executed.stderr)
                self.assertNotIn(origin, executed.stderr, "debug diagnostics leaked a source URL")
                self.assertEqual(json.loads(executed.stdout)["status"], "completed")
                self.assertEqual(hits["/jobs"], 1)
                pages = json.loads(invoke(root, "runs", "pages", run_id).stdout)
                self.assertEqual({page["url"] for page in pages}, {origin + "/", origin + "/jobs"})

            results = invoke(root, "runs", "results", run_id)
            self.assertEqual(results.returncode, 0, results.stderr)
            items = json.loads(results.stdout)
            self.assertEqual([item["title"] for item in items],
                             ["Platform Engineer", "Remote Product Designer"])
            self.assertEqual(items[0]["source_url"], origin + "/jobs")
            ref = items[0]["artifact_ref"]
            artifact = invoke(root, "runs", "artifact", run_id, "--ref", ref)
            self.assertEqual(artifact.returncode, 0, artifact.stderr)
            self.assertIn("JobPosting", json.loads(artifact.stdout)["html"])
            rerun = invoke(root, "runs", "extract", run_id)
            self.assertEqual(rerun.returncode, 0, rerun.stderr)
            self.assertEqual(json.loads(rerun.stdout), items)
            report = json.loads(invoke(root, "runs", "report", run_id).stdout)
            self.assertEqual(report["pages_saved"], 2)
            self.assertEqual(report["items_extracted"], 2)

    def test_execution_needs_approval_and_a_terminal_run_cannot_refetch(self):
        with tempfile.TemporaryDirectory() as directory, fixture_site() as (origin, hits):
            root = Path(directory)
            created = invoke(root, "runs", "create", "--seed", origin + "/jobs", "--allow-local")
            run_id = json.loads(created.stdout)["id"]
            refused = invoke(root, "runs", "execute", run_id)
            self.assertNotEqual(refused.returncode, 0)
            self.assertEqual(sum(hits.values()), 0)
            self.assertEqual(json.loads(invoke(root, "runs", "show", run_id).stdout)["status"], "pending")
            done = invoke(root, "runs", "execute", run_id, "--approve")
            self.assertEqual(done.returncode, 0, done.stderr)
            request_count = sum(hits.values())
            repeated = invoke(root, "runs", "execute", run_id, "--approve")
            self.assertNotEqual(repeated.returncode, 0)
            self.assertEqual(sum(hits.values()), request_count)

    def test_partial_results_survive_a_failed_page(self):
        with tempfile.TemporaryDirectory() as directory, fixture_site() as (origin, hits):
            root = Path(directory)
            created = invoke(root, "runs", "create", "--seed", origin + "/mixed", "--allow-local")
            run_id = json.loads(created.stdout)["id"]
            done = invoke(root, "runs", "execute", run_id, "--approve")
            self.assertEqual(done.returncode, 1, done.stderr)
            self.assertEqual(json.loads(done.stdout)["status"], "partial")
            self.assertEqual(hits["/failure"], 2)
            items = json.loads(invoke(root, "runs", "results", run_id).stdout)
            self.assertEqual([item["title"] for item in items],
                             ["Platform Engineer", "Remote Product Designer"])
            report = json.loads(invoke(root, "runs", "report", run_id).stdout)
            self.assertEqual(report["failed_requests"], 1)

    def test_timeout_persists_failure_without_reporting_success(self):
        with tempfile.TemporaryDirectory() as directory, fixture_site() as (origin, _hits):
            root = Path(directory)
            created = invoke(root, "runs", "create", "--seed", origin + "/slow",
                             "--allow-local", "--timeout-seconds", "1")
            run_id = json.loads(created.stdout)["id"]
            done = invoke(root, "runs", "execute", run_id, "--approve")
            self.assertEqual(done.returncode, 1, done.stderr)
            self.assertEqual(json.loads(done.stdout)["status"], "failed")
            report = json.loads(invoke(root, "runs", "report", run_id).stdout)
            self.assertEqual(report["error"], "collection timed out")

    @unittest.skipUnless(os.name == "posix", "SIGINT lifecycle check uses POSIX signals")
    def test_interrupt_marks_run_cancelled_and_releases_local_lock(self):
        with tempfile.TemporaryDirectory() as directory, fixture_site() as (origin, hits):
            root = Path(directory)
            created = invoke(root, "runs", "create", "--seed", origin + "/slow", "--allow-local")
            run_id = json.loads(created.stdout)["id"]
            env = os.environ.copy()
            env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
            process = subprocess.Popen([sys.executable, "-m", "jevscout", "--data-dir", str(root),
                                        "runs", "execute", run_id, "--approve"],
                                       env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            try:
                deadline = time.monotonic() + 10
                while hits["/slow"] == 0 and process.poll() is None and time.monotonic() < deadline:
                    time.sleep(0.02)
                self.assertGreater(hits["/slow"], 0, "collection did not start")
                process.send_signal(signal.SIGINT)
                _stdout, stderr = process.communicate(timeout=15)
                self.assertEqual(process.returncode, 130, stderr)
                shown = invoke(root, "runs", "show", run_id)
                self.assertEqual(json.loads(shown.stdout)["status"], "cancelled")
                # A subsequent extraction obtains the same operation lock.
                extracted = invoke(root, "runs", "extract", run_id)
                self.assertEqual(extracted.returncode, 0, extracted.stderr)
            finally:
                if process.poll() is None:
                    process.kill()
                    process.communicate(timeout=5)
