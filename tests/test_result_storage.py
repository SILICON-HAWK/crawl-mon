import json
import multiprocessing
import tempfile
import unittest
from pathlib import Path

from jevscout.models import RunSpec
from jevscout.storage import FileRunStore


def _try_operation_lock(root: str, results) -> None:
    try:
        with FileRunStore(Path(root)).operation_lock():
            results.put("acquired")
    except RuntimeError as exc:
        results.put(str(exc))


class ExecutionAndResultStorageTests(unittest.TestCase):
    def test_engine_workspace_is_created_and_isolated_per_run(self):
        with tempfile.TemporaryDirectory() as directory:
            store = FileRunStore(Path(directory))
            first = store.create(RunSpec(["https://example.test/one"]))
            second = store.create(RunSpec(["https://example.test/two"]))

            first_workspace = store.engine_workspace(first.id)
            second_workspace = store.engine_workspace(second.id)

            self.assertEqual(first_workspace.name, "engine")
            self.assertEqual(first_workspace.parent.name, first.id)
            self.assertEqual(second_workspace.parent.name, second.id)
            self.assertNotEqual(first_workspace, second_workspace)
            self.assertTrue(first_workspace.is_dir())
            self.assertEqual(first_workspace, first_workspace.resolve())
            with self.assertRaises(FileNotFoundError):
                store.engine_workspace("00000000-0000-0000-0000-000000000000")

    def test_execution_and_results_round_trip_from_a_fresh_store(self):
        with tempfile.TemporaryDirectory() as directory:
            store = FileRunStore(Path(directory))
            run = store.create(RunSpec(["https://example.test/jobs"]))
            execution = {"status": "completed", "pages_seen": 2}
            items = [{"title": "Platform Engineer"}, {"title": "Product Designer"}]

            self.assertIsNone(store.read_execution(run.id))
            self.assertEqual(store.list_results(run.id), [])
            store.write_execution(run.id, execution)
            store.save_results(run.id, items)

            reopened = FileRunStore(Path(directory))
            self.assertEqual(reopened.read_execution(run.id), execution)
            self.assertEqual(reopened.list_results(run.id), items)
            saved = json.loads((Path(directory) / "runs" / run.id / "results.json").read_text())
            self.assertEqual(
                saved,
                {"schema_version": 1, "parser_version": "jsonld-jobs-v1", "items": items},
            )

    def test_invalid_writes_preserve_prior_data_and_missing_runs_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            store = FileRunStore(Path(directory))
            run = store.create(RunSpec(["https://example.test/jobs"]))
            store.write_execution(run.id, {"status": "completed"})
            store.save_results(run.id, [{"title": "Existing result"}])

            with self.assertRaises((TypeError, ValueError)):
                store.write_execution(run.id, {"score": float("nan")})
            with self.assertRaises((TypeError, ValueError)):
                store.save_results(run.id, [{"score": float("nan")}])
            with self.assertRaises((TypeError, ValueError)):
                store.write_execution(run.id, ["not", "an", "object"])
            with self.assertRaises((TypeError, ValueError)):
                store.save_results(run.id, ["not an object"])

            self.assertEqual(store.read_execution(run.id), {"status": "completed"})
            self.assertEqual(store.list_results(run.id), [{"title": "Existing result"}])
            missing_id = "00000000-0000-0000-0000-000000000000"
            with self.assertRaises(FileNotFoundError):
                store.write_execution(missing_id, {})
            with self.assertRaises(FileNotFoundError):
                store.save_results(missing_id, [])
            with self.assertRaises(FileNotFoundError):
                store.list_results(missing_id)

    def test_operation_lock_excludes_another_process_and_releases_after_errors(self):
        with tempfile.TemporaryDirectory() as directory:
            store = FileRunStore(Path(directory))
            queue = multiprocessing.Queue()
            with store.operation_lock():
                process = multiprocessing.Process(
                    target=_try_operation_lock, args=(directory, queue)
                )
                process.start()
                self.assertEqual(queue.get(timeout=5), "another local operation is active")
                process.join(timeout=5)
                self.assertEqual(process.exitcode, 0)

            with self.assertRaisesRegex(ValueError, "release after exception"):
                with store.operation_lock():
                    raise ValueError("release after exception")

            acquired = multiprocessing.Process(
                target=_try_operation_lock, args=(directory, queue)
            )
            acquired.start()
            self.assertEqual(queue.get(timeout=5), "acquired")
            acquired.join(timeout=5)
            self.assertEqual(acquired.exitcode, 0)
            queue.close()


if __name__ == "__main__":
    unittest.main()
