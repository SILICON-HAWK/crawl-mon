"""Unit tests for the parallel multi-provider job fetcher."""
import asyncio
import os
import tempfile
import unittest
from pathlib import Path

from jevscout.application.parallel_fetch import (
    DomainRateLimiter,
    ParallelJobFetcher,
    parse_duration,
)
from jevscout.storage.filesystem import FileRunStore


class ParallelFetchTests(unittest.TestCase):
    def test_parse_duration(self):
        self.assertEqual(parse_duration("30s"), 30.0)
        self.assertEqual(parse_duration("15m"), 900.0)
        self.assertEqual(parse_duration("2h"), 7200.0)
        self.assertEqual(parse_duration("1.5h"), 5400.0)
        self.assertEqual(parse_duration("1d"), 86400.0)
        with self.assertRaises(ValueError):
            parse_duration("invalid")

    def test_domain_rate_limiter_pacing(self):
        async def run():
            limiter = DomainRateLimiter(requests_per_second=10.0)
            t0 = asyncio.get_event_loop().time()
            await limiter.wait()
            await limiter.wait()
            t1 = asyncio.get_event_loop().time()
            self.assertGreaterEqual(t1 - t0, 0.08)

        asyncio.run(run())

    def test_parallel_fetcher_mock_sweep(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Simple mock feed payloads
            mock_feeds = {
                "remoteok:test": {
                    "url": "https://remoteok.com/api?tag=dev",
                    "provider": "remoteok",
                    "min_interval_seconds": 0,
                },
                "greenhouse:test": {
                    "url": "https://boards-api.greenhouse.io/v1/boards/test/jobs?content=true",
                    "provider": "greenhouse",
                    "min_interval_seconds": 0,
                },
            }

            def mock_requester(url: str):
                if "remoteok.com" in url:
                    return 200, '[{"legal":"Remote OK"},{"id":"101","position":"Software Engineer","company":"Acme","url":"https://remoteok.com/j/101","location":"Worldwide Remote"}]'
                elif "greenhouse.io" in url:
                    return 200, '{"jobs":[{"id":202,"title":"Backend Developer","absolute_url":"https://job.url/202","departments":[],"offices":[],"location":{"name":"Bengaluru, India"}}]}'
                return 404, "Not Found"

            fetcher = ParallelJobFetcher(
                data_dir=temp_path,
                feeds=mock_feeds,
                max_concurrent=2,
                requester=mock_requester,
            )

            results = asyncio.run(fetcher.run_once())
            self.assertEqual(len(results), 2)
            self.assertTrue(all(r.status == "completed" for r in results))

            store = FileRunStore(temp_path)
            runs = store.list_runs()
            self.assertEqual(len(runs), 2)

            all_results = []
            for r in runs:
                all_results.extend(store.list_results(r.id))
            self.assertGreaterEqual(len(all_results), 2)


if __name__ == "__main__":
    unittest.main()
