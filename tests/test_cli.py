"""Public command-line behavior using real filesystem storage."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def invoke(data_dir: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_ROOT / "src")
    return subprocess.run(
        [sys.executable, "-m", "jevscout", "--data-dir", str(data_dir), *arguments],
        cwd=PROJECT_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


class CliTests(unittest.TestCase):
    def test_create_then_show_and_list_persist_pending_spec(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            data_dir = Path(directory)
            created = invoke(
                data_dir,
                "runs",
                "create",
                "--seed",
                "https://example.test/jobs",
                "--seed",
                "https://example.test/roles",
                "--max-pages",
                "7",
                "--max-depth",
                "2",
                "--timeout-seconds",
                "45",
            )

            self.assertEqual(created.returncode, 0, created.stderr)
            record = json.loads(created.stdout)
            run_id = record["id"]
            self.assertEqual(
                record["spec"],
                {
                    "seed_urls": ["https://example.test/jobs", "https://example.test/roles"],
                    "max_pages": 7,
                    "max_depth": 2,
                    "timeout_seconds": 45,
                },
            )
            self.assertEqual(record["status"], "pending")

            shown = invoke(data_dir, "runs", "show", run_id)
            listed = invoke(data_dir, "runs", "list")
            self.assertEqual(shown.returncode, 0, shown.stderr)
            self.assertEqual(listed.returncode, 0, listed.stderr)
            self.assertEqual(json.loads(shown.stdout), record)
            self.assertEqual(json.loads(listed.stdout), [record])

    def test_invalid_limits_and_credential_url_fail_without_persisting_or_leaking_input(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            data_dir = Path(directory)
            invalid_limit = invoke(
                data_dir, "runs", "create", "--seed", "https://example.test", "--max-pages", "0"
            )
            credential_url = "https://private-token@example.test/jobs"
            invalid_url = invoke(data_dir, "runs", "create", "--seed", credential_url)

            for result in (invalid_limit, invalid_url):
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, "")
                self.assertNotIn("Traceback", result.stderr)
            self.assertNotIn(credential_url, invalid_url.stderr)
            listed = invoke(data_dir, "runs", "list")
            self.assertEqual(listed.returncode, 0, listed.stderr)
            self.assertEqual(json.loads(listed.stdout), [])

    def test_invalid_run_id_is_a_safe_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = invoke(Path(directory), "runs", "show", "../../private")

            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(result.stdout, "")
            self.assertIn("error", result.stderr.lower())
            self.assertNotIn("../../private", result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    def test_malformed_stored_record_is_a_safe_error_for_show_and_list(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            data_dir = Path(directory)
            created = invoke(data_dir, "runs", "create", "--seed", "https://example.test")
            self.assertEqual(created.returncode, 0, created.stderr)
            run_id = json.loads(created.stdout)["id"]
            (data_dir / "runs" / run_id / "run.json").write_text("{}\n", encoding="utf-8")

            for arguments in (("runs", "show", run_id), ("runs", "list")):
                with self.subTest(arguments=arguments):
                    result = invoke(data_dir, *arguments)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertEqual(result.stdout, "")
                    self.assertNotIn("Traceback", result.stderr)
                    self.assertIn("error", result.stderr.lower())


if __name__ == "__main__":
    unittest.main()
