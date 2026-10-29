"""Application failure handling at the external engine and saved-data boundaries."""

import asyncio
from pathlib import Path
import tempfile
import unittest

from jevscout.application import execute_run
from jevscout.engine import PageEvidence
from jevscout.models import RunSpec
from jevscout.storage import FileRunStore


class ApplicationTests(unittest.IsolatedAsyncioTestCase):
    async def test_timeout_and_unusable_saved_metadata_still_leave_a_terminal_run(self):
        with tempfile.TemporaryDirectory() as directory:
            store = FileRunStore(Path(directory))
            run = store.create(RunSpec(["https://example.test/jobs"]))

            class TimedOutEngine:
                name = "timeout-fixture"
                version = "1"

                async def collect(self, spec, on_page, *, work_dir):
                    on_page(PageEvidence(spec.seed_urls[0], "<html>saved evidence</html>", 200, 0))
                    # Simulate unusable metadata at the filesystem boundary while
                    # a network timeout is being handled, not an internal mock.
                    store.save_page(run.id, "https://example.test/bad", "corrupted evidence",
                                    {"status_code": "invalid"})
                    raise asyncio.TimeoutError

            finished = await execute_run(store, run.id, approved=True, engine=TimedOutEngine())
            self.assertEqual(finished.status, "partial")
            self.assertEqual(store.get(run.id).status, "partial")
            self.assertEqual(store.read_execution(run.id)["error"],
                             "collection timed out; extraction failed")
