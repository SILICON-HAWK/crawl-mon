import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from jevscout.models import RunRecord, RunSpec
from jevscout.storage import FileRunStore


class RunSpecTests(unittest.TestCase):
    def test_valid_spec_round_trips_as_plain_data(self):
        spec = RunSpec(["https://example.com/jobs"], max_pages=25, max_depth=3, timeout_seconds=120)

        self.assertEqual(
            spec.to_dict(),
            {
                "seed_urls": ["https://example.com/jobs"],
                "max_pages": 25,
                "max_depth": 3,
                "timeout_seconds": 120,
            },
        )
        self.assertEqual(RunSpec.from_dict(spec.to_dict()), spec)

    def test_rejects_invalid_or_unknown_spec_fields(self):
        invalid_specs = [
            {"seed_urls": []},
            {"seed_urls": ["file:///tmp/page"]},
            {"seed_urls": ["https://user:pass@example.com"]},
            {"seed_urls": ["https://:443"]},
            {"seed_urls": ["https://example.com:bad"]},
            {"seed_urls": ["https://[2001:db8::1"]},
            {"seed_urls": ["https://example.com\\\\evil"]},
            {"seed_urls": ["https://example.com/\npath"]},
            {"seed_urls": ["https://example.com"], "max_pages": 1001},
            {"seed_urls": ["https://example.com"], "max_depth": -1},
            {"seed_urls": ["https://example.com"], "timeout_seconds": 3601},
            {"seed_urls": ["https://example.com"], "unexpected": True},
        ]

        for payload in invalid_specs:
            with self.subTest(payload=payload):
                with self.assertRaises((TypeError, ValueError)):
                    RunSpec.from_dict(payload)

    def test_accepts_uppercase_http_scheme(self):
        self.assertEqual(RunSpec(["HTTPS://example.com/jobs"]).seed_urls, ["HTTPS://example.com/jobs"])

    def test_rejects_unknown_run_status(self):
        with self.assertRaises(ValueError):
            RunRecord(id="run-id", spec=RunSpec(["https://example.com"]), status="queued-ish")


class FileRunStoreTests(unittest.TestCase):
    def test_created_run_can_be_read_from_another_store_instance(self):
        with tempfile.TemporaryDirectory() as directory:
            first_store = FileRunStore(Path(directory))
            created = first_store.create(RunSpec(["https://example.com/jobs"]))

            second_store = FileRunStore(Path(directory))
            self.assertEqual(second_store.get(created.id), created)
            self.assertEqual(second_store.list_runs(), [created])

    def test_created_run_uses_a_spec_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            store = FileRunStore(Path(directory))
            urls = ["https://example.com/jobs"]
            created = store.create(RunSpec(urls))

            urls.append("https://elsewhere.example/jobs")

            self.assertEqual(created.spec.seed_urls, ["https://example.com/jobs"])
            self.assertEqual(store.get(created.id).spec.seed_urls, ["https://example.com/jobs"])

    def test_run_updates_are_visible_after_reopening_store(self):
        with tempfile.TemporaryDirectory() as directory:
            store = FileRunStore(Path(directory))
            created = store.create(RunSpec(["https://example.com/jobs"]))
            finished = replace(created, status="completed")

            store.update(finished)

            self.assertEqual(FileRunStore(Path(directory)).get(created.id), finished)

    def test_page_html_and_metadata_round_trip_with_original_url(self):
        url = "https://example.com/jobs?q=research+engineer"
        metadata = {"status_code": 200, "depth": 1}
        with tempfile.TemporaryDirectory() as directory:
            store = FileRunStore(Path(directory))
            run = store.create(RunSpec([url]))

            ref = store.save_page(run.id, url, "<html>jobs</html>", metadata)

            reopened = FileRunStore(Path(directory))
            self.assertEqual(reopened.read_artifact(run.id, ref), "<html>jobs</html>")
            self.assertEqual(
                reopened.list_pages(run.id),
                [{"url": url, "artifact_ref": ref, "metadata": metadata}],
            )

    def test_changed_html_preserves_old_evidence_and_same_input_reuses_reference(self):
        url = "https://example.com/jobs"
        with tempfile.TemporaryDirectory() as directory:
            store = FileRunStore(Path(directory))
            run = store.create(RunSpec([url]))

            original_ref = store.save_page(run.id, url, "<html>first</html>", {"version": 1})
            updated_ref = store.save_page(run.id, url, "<html>second</html>", {"version": 2})
            repeated_ref = store.save_page(run.id, url, "<html>second</html>", {"version": 2})

            self.assertNotEqual(original_ref, updated_ref)
            self.assertEqual(updated_ref, repeated_ref)
            self.assertEqual(store.read_artifact(run.id, original_ref), "<html>first</html>")
            self.assertEqual(store.read_artifact(run.id, updated_ref), "<html>second</html>")
            self.assertEqual(len(store.list_pages(run.id)), 2)

    def test_changed_metadata_preserves_both_observations(self):
        url = "https://example.com/jobs"
        html = "<html>same page</html>"
        with tempfile.TemporaryDirectory() as directory:
            store = FileRunStore(Path(directory))
            run = store.create(RunSpec([url]))

            first_ref = store.save_page(run.id, url, html, {"status_code": 200})
            second_ref = store.save_page(run.id, url, html, {"status_code": 304})

            self.assertNotEqual(first_ref, second_ref)
            pages = store.list_pages(run.id)
            self.assertEqual(
                {page["artifact_ref"]: page["metadata"] for page in pages},
                {first_ref: {"status_code": 200}, second_ref: {"status_code": 304}},
            )
            self.assertEqual(store.read_artifact(run.id, first_ref), html)
            self.assertEqual(store.read_artifact(run.id, second_ref), html)

    def test_rejects_credential_url_without_creating_artifacts(self):
        with tempfile.TemporaryDirectory() as directory:
            store = FileRunStore(Path(directory))
            run = store.create(RunSpec(["https://example.com/jobs"]))

            with self.assertRaises(ValueError):
                store.save_page(run.id, "https://user:secret@example.com/jobs", "<html />", {})

            self.assertEqual(store.list_pages(run.id), [])

    def test_rejects_non_json_metadata_without_creating_artifacts(self):
        with tempfile.TemporaryDirectory() as directory:
            store = FileRunStore(Path(directory))
            run = store.create(RunSpec(["https://example.com/jobs"]))

            with self.assertRaises(ValueError):
                store.save_page(run.id, "https://example.com/jobs", "<html />", {"score": float("nan")})

            self.assertEqual(store.list_pages(run.id), [])

    def test_rejects_unsafe_run_ids_and_artifact_references(self):
        with tempfile.TemporaryDirectory() as directory:
            store = FileRunStore(Path(directory))

            with self.assertRaises(ValueError):
                store.get("../outside")
            with self.assertRaises(ValueError):
                store.read_artifact("00000000-0000-0000-0000-000000000000", "../../outside")
