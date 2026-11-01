"""Parallel long-running collection across all ATS providers and Wellfound.

Supports continuous execution for a configurable duration (e.g. 2h, 30m)
with parallel asynchronous network fetching, domain-level rate limiting,
and safe serialized storage writes.
"""
from __future__ import annotations

import argparse
import asyncio
import fcntl
import json
import logging
import os
import re
import signal
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from jevscout.core.models import RunSpec
from jevscout.storage.filesystem import FileRunStore
from jevscout.application.operations import _extract

logger = logging.getLogger("jevscout.parallel_fetch")

# Curated feeds across all 8 supported providers with India-focused priority
DEFAULT_FEEDS: dict[str, dict[str, Any]] = {
    # 1. RemoteOK (Global & India-eligible remote dev jobs)
    "remoteok:dev": {
        "url": "https://remoteok.com/api?tag=dev",
        "provider": "remoteok",
        "min_interval_seconds": 600,
    },
    # 2. Greenhouse (Companies with prominent India engineering hubs)
    "greenhouse:sonicwall": {
        "url": "https://boards-api.greenhouse.io/v1/boards/sonicwall/jobs?content=true",
        "provider": "greenhouse",
        "min_interval_seconds": 1800,
    },
    "greenhouse:stripe": {
        "url": "https://boards-api.greenhouse.io/v1/boards/stripe/jobs?content=true",
        "provider": "greenhouse",
        "min_interval_seconds": 1800,
    },
    "greenhouse:thoughtworks": {
        "url": "https://boards-api.greenhouse.io/v1/boards/thoughtworks/jobs?content=true",
        "provider": "greenhouse",
        "min_interval_seconds": 1800,
    },
    "greenhouse:rubrik": {
        "url": "https://boards-api.greenhouse.io/v1/boards/rubrik/jobs?content=true",
        "provider": "greenhouse",
        "min_interval_seconds": 1800,
    },
    # 3. Ashby
    "ashby:firstwork": {
        "url": "https://api.ashbyhq.com/posting-api/job-board/firstwork?includeCompensation=true",
        "provider": "ashby",
        "min_interval_seconds": 1800,
    },
    "ashby:linear": {
        "url": "https://api.ashbyhq.com/posting-api/job-board/linear?includeCompensation=true",
        "provider": "ashby",
        "min_interval_seconds": 1800,
    },
    "ashby:ramp": {
        "url": "https://api.ashbyhq.com/posting-api/job-board/ramp?includeCompensation=true",
        "provider": "ashby",
        "min_interval_seconds": 1800,
    },
    # 4. Lever
    "lever:hotstar": {
        "url": "https://api.lever.co/v0/postings/hotstar?mode=json",
        "provider": "lever",
        "min_interval_seconds": 1800,
    },
    "lever:spotify": {
        "url": "https://api.lever.co/v0/postings/spotify?mode=json",
        "provider": "lever",
        "min_interval_seconds": 1800,
    },
    # 5. Recruitee
    "recruitee:transperfect": {
        "url": "https://transperfect.recruitee.com/api/offers/",
        "provider": "recruitee",
        "min_interval_seconds": 1800,
    },
    # 6. Breezy HR
    "breezy:nexthire": {
        "url": "https://nexthire.breezy.hr/json",
        "provider": "breezy",
        "min_interval_seconds": 1800,
    },
    # 7. Teamtailor
    "teamtailor:invision": {
        "url": "https://invision.teamtailor.com/jobs.json",
        "provider": "teamtailor",
        "min_interval_seconds": 1800,
    },
    # 8. Wellfound Crawler (explicitly scoped to India startup tech roles)
    "wellfound:software-engineer-india": {
        "url": "https://wellfound.com/role/l/software-engineer/india",
        "provider": "wellfound",
        "min_interval_seconds": 1800,
    },
    "wellfound:full-stack-india": {
        "url": "https://wellfound.com/role/l/full-stack-engineer/india",
        "provider": "wellfound",
        "min_interval_seconds": 1800,
    },
    "wellfound:backend-india": {
        "url": "https://wellfound.com/role/l/backend-engineer/india",
        "provider": "wellfound",
        "min_interval_seconds": 1800,
    },
}

_DURATION_RE = re.compile(r"^(\d+(?:\.\d+)?)\s*([smhd]?)$", re.IGNORECASE)


def parse_duration(value: str) -> float:
    """Parse duration strings like '2h', '90m', '3600s', '1.5d' to seconds."""
    match = _DURATION_RE.match(value.strip())
    if not match:
        raise ValueError(f"Invalid duration format: '{value}'. Use e.g. '2h', '30m', '3600s'.")
    num_str, unit = match.groups()
    num = float(num_str)
    unit = unit.lower()
    if unit in {"", "s"}:
        return num
    elif unit == "m":
        return num * 60
    elif unit == "h":
        return num * 3600
    elif unit == "d":
        return num * 86400
    raise ValueError(f"Unknown time unit: '{unit}'")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class DomainRateLimiter:
    """Token-bucket per-domain rate limiter."""
    def __init__(self, requests_per_second: float = 1.0):
        self.interval = 1.0 / max(0.1, requests_per_second)
        self._last_request: float = 0.0
        self._lock = asyncio.Lock()

    async def wait(self) -> None:
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_request
            if elapsed < self.interval:
                await asyncio.sleep(self.interval - elapsed)
            self._last_request = time.monotonic()


@dataclass
class FetchResult:
    key: str
    provider: str
    url: str
    status: str
    items_extracted: int = 0
    run_id: str | None = None
    error: str | None = None
    duration_seconds: float = 0.0


class ParallelJobFetcher:
    """Coordinates parallel network fetching across multiple ATS providers."""

    def __init__(
        self,
        data_dir: Path,
        feeds: dict[str, dict[str, Any]] | None = None,
        max_concurrent: int = 4,
        requester: Callable[[str], Any] | None = None,
        india_only: bool = True,
    ):
        self.data_dir = Path(data_dir).resolve()
        self.store = FileRunStore(self.data_dir)
        self.feeds = feeds or DEFAULT_FEEDS
        self.max_concurrent = max_concurrent
        self.requester = requester
        self.india_only = india_only
        self._storage_lock = asyncio.Lock()
        self._stop_event = asyncio.Event()

        # Domain limiters (polite crawls)
        self._limiters: dict[str, DomainRateLimiter] = {
            "lever": DomainRateLimiter(1.0),       # Lever robots.txt requires 1 req/sec
            "greenhouse": DomainRateLimiter(2.0),
            "ashby": DomainRateLimiter(2.0),
            "wellfound": DomainRateLimiter(0.2),   # 1 req per 5 sec
            "default": DomainRateLimiter(2.0),
        }

        # Track attempt history: key -> last_attempt_timestamp
        self._last_attempts: dict[str, float] = {}

    def stop(self) -> None:
        self._stop_event.set()

    def is_stopped(self) -> bool:
        return self._stop_event.is_set()

    async def _fetch_url(self, url: str) -> tuple[int, str]:
        if self.requester is not None:
            res = self.requester(url)
            if asyncio.iscoroutine(res):
                return await res
            return res

        import httpx
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 (JevScout-Crawler/1.0)"
            ),
            "Accept": "application/json, text/html;q=0.9, */*;q=0.8",
        }
        # Support environment proxy if configured
        proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY") or None
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True, proxy=proxy, headers=headers) as client:
            resp = await client.get(url)
            return resp.status_code, resp.text

    async def _process_feed(self, key: str, spec: dict[str, Any]) -> FetchResult:
        url = spec["url"]
        provider = spec["provider"]
        limiter = self._limiters.get(provider, self._limiters["default"])
        start_time = time.monotonic()

        try:
            await limiter.wait()
            if self.is_stopped():
                return FetchResult(key, provider, url, "cancelled")

            status_code, text = await self._fetch_url(url)
            if not 200 <= status_code < 300:
                return FetchResult(
                    key, provider, url, "failed",
                    error=f"HTTP {status_code}",
                    duration_seconds=time.monotonic() - start_time
                )

            # Atomic, safe storage write serialized via async lock
            async with self._storage_lock:
                record = self.store.create(RunSpec(
                    [url], max_pages=1, max_depth=0, timeout_seconds=60, allow_local=False
                ))
                self.store.save_page(record.id, url, text, {"status_code": status_code, "depth": 0})
                feed_india_only = self.india_only if provider != "wellfound" else False
                items = _extract(self.store, record.id, india_only=feed_india_only)

                execution_report = {
                    "schema_version": 1,
                    "engine": "parallel-fetcher",
                    "provider": provider,
                    "started_at": _now_iso(),
                    "finished_at": _now_iso(),
                    "pages_saved": 1,
                    "items_extracted": len(items),
                    "failed_requests": 0,
                    "status": "completed",
                }
                self.store.write_execution(record.id, execution_report)
                self.store.update(record)

            duration = time.monotonic() - start_time
            return FetchResult(
                key, provider, url, "completed",
                items_extracted=len(items),
                run_id=record.id,
                duration_seconds=duration,
            )

        except Exception as exc:
            duration = time.monotonic() - start_time
            return FetchResult(
                key, provider, url, "failed",
                error=str(exc)[:200],
                duration_seconds=duration,
            )

    async def run_once(self) -> list[FetchResult]:
        """Run a single parallel sweep across all eligible feeds."""
        now = time.monotonic()
        eligible = []
        for key, spec in self.feeds.items():
            last = self._last_attempts.get(key, 0.0)
            min_interval = spec.get("min_interval_seconds", 60)
            if now - last >= min_interval:
                eligible.append((key, spec))

        if not eligible:
            return []

        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def worker(key: str, spec: dict[str, Any]) -> FetchResult:
            async with semaphore:
                res = await self._process_feed(key, spec)
                self._last_attempts[key] = time.monotonic()
                return res

        tasks = [worker(k, s) for k, s in eligible]
        results = await asyncio.gather(*tasks, return_exceptions=False)
        return results

    async def run_duration(self, duration_seconds: float) -> dict[str, Any]:
        """Run continuously until duration expires or stop requested."""
        start_time = time.monotonic()
        deadline = start_time + duration_seconds
        total_runs = 0
        total_items = 0
        provider_counts: dict[str, int] = {}

        print(f"[*] Starting parallel fetcher across {len(self.feeds)} feeds")
        print(f"[*] Target duration: {duration_seconds/3600:.2f} hours ({duration_seconds:.0f}s)")
        print(f"[*] Data directory: {self.data_dir}\n")

        while not self.is_stopped() and time.monotonic() < deadline:
            sweep_results = await self.run_once()
            for r in sweep_results:
                if r.status == "completed":
                    total_runs += 1
                    total_items += r.items_extracted
                    provider_counts[r.provider] = provider_counts.get(r.provider, 0) + r.items_extracted
                    print(
                        f"[{datetime.now().strftime('%H:%M:%S')}] ✓ [{r.provider}] {r.key}: "
                        f"{r.items_extracted} jobs extracted (Run: {r.run_id[:8]}... in {r.duration_seconds:.1f}s)"
                    )
                elif r.status == "failed":
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] ✗ [{r.provider}] {r.key} failed: {r.error}")

            remaining = deadline - time.monotonic()
            if remaining <= 0 or self.is_stopped():
                break

            # Sleep in small slices to respond promptly to stop signals
            sleep_slice = min(15.0, remaining)
            await asyncio.sleep(sleep_slice)

        elapsed = time.monotonic() - start_time
        print("\n" + "=" * 60)
        print(f"[*] Parallel fetch completed in {elapsed/3600:.2f}h ({elapsed:.1f}s)")
        print(f"[*] Total successful collection runs: {total_runs}")
        print(f"[*] Total jobs extracted: {total_items}")
        print("[*] Jobs breakdown by provider:")
        for prov, cnt in sorted(provider_counts.items(), key=lambda x: -x[1]):
            print(f"    - {prov:12s}: {cnt:5d} jobs")
        print("=" * 60)

        return {
            "total_runs": total_runs,
            "total_jobs": total_items,
            "elapsed_seconds": elapsed,
            "provider_breakdown": provider_counts,
        }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Parallel long-running collection across all ATS providers and Wellfound"
    )
    parser.add_argument(
        "--data-dir", type=Path, default=Path(os.environ.get("JEVSCOUT_DATA_DIR", "data/live-trial")),
        help="Path to runs data root",
    )
    parser.add_argument(
        "--duration", "-d", "-t", type=str, default="2h",
        help="How long to run the parallel fetcher (e.g. 2h, 30m, 3600s, 1d). Default: 2h",
    )
    parser.add_argument(
        "--concurrency", "-c", type=int, default=4,
        help="Maximum parallel fetch requests at once. Default: 4",
    )
    parser.add_argument(
        "--once", action="store_true",
        help="Run exactly one sweep across all feeds and exit immediately",
    )
    parser.add_argument(
        "--india-only", action="store_true", default=True,
        help="Filter extracted jobs for India locations and India-eligible remote (default: True)",
    )
    parser.add_argument(
        "--all-locations", dest="india_only", action="store_false",
        help="Disable India filtering and save all global locations",
    )
    parser.add_argument(
        "--approve", action="store_true",
        help="Explicitly authorize network execution",
    )
    args = parser.parse_args()

    if not args.approve:
        parser.error("Network collection requires explicit authorization. Pass --approve.")

    duration_sec = 0.0 if args.once else parse_duration(args.duration)
    data_dir = args.data_dir.resolve()
    data_dir.mkdir(parents=True, exist_ok=True, mode=0o700)

    # Process-level advisory lock to prevent duplicate parallel fetchers
    lock_file = (data_dir / ".parallel_fetch.lock").open("a+b")
    try:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print("[!] Error: Another parallel fetcher process is already running for this data directory.")
        sys.exit(1)

    fetcher = ParallelJobFetcher(
        data_dir=data_dir,
        max_concurrent=args.concurrency,
        india_only=args.india_only,
    )

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    def handle_signal(*_):
        print("\n[!] Stop signal received. Finishing in-flight requests cleanly...")
        fetcher.stop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, handle_signal)
        except NotImplementedError:
            signal.signal(sig, handle_signal)

    try:
        if args.once:
            res = loop.run_until_complete(fetcher.run_once())
            total = sum(r.items_extracted for r in res if r.status == "completed")
            print(f"\n[*] Finished single sweep: {total} total jobs extracted across {len(res)} feeds.")
        else:
            loop.run_until_complete(fetcher.run_duration(duration_sec))
    finally:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
        lock_file.close()


if __name__ == "__main__":
    main()
