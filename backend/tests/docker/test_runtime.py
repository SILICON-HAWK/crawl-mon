"""Packaging checks enabled only in the Docker test target."""
import os
import subprocess
import tempfile
import unittest


@unittest.skipUnless(os.environ.get("JEVSCOUT_CONTAINER_TEST") == "1", "requires Docker test image")
class DockerRuntimeTests(unittest.TestCase):
    def test_nonroot_cli_has_installed_dependencies_and_writable_storage(self):
        import crawlee
        import psycopg

        self.assertNotEqual(os.getuid(), 0)
        with tempfile.TemporaryDirectory(dir="/data") as directory:
            result = subprocess.run(
                ["jevscout", "--data-dir", directory, "runs", "list"],
                text=True, capture_output=True, timeout=30, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), "[]")
