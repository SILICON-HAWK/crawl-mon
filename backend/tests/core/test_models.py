import unittest

from jevscout.core.models import RunRecord, RunSpec


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
                "allow_local": False,
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


