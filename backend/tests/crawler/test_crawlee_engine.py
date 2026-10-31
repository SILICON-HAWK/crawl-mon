from __future__ import annotations

import asyncio
import socket
import threading
import time
import unittest
from collections import Counter
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from jevscout.core.engine import PageEvidence
from jevscout.core.models import RunSpec

try:
    import httpcore2
    from jevscout.adapters.crawling.crawlee import CrawleeEngine, _ScopedAnyIOBackend
except ImportError:
    CrawleeEngine = None
    _ScopedAnyIOBackend = None
    httpcore2 = None


class Site:
    def __init__(
        self,
        routes: dict[str, tuple[int, str, dict[str, str]]],
        *,
        slow_paths: set[str] | None = None,
        delay_seconds: float = 0,
    ):
        self.routes = routes
        self.slow_paths = slow_paths or set()
        self.delay_seconds = delay_seconds
        self.hits: Counter[str] = Counter()
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                owner.hits[self.path] += 1
                if self.path in owner.slow_paths:
                    time.sleep(owner.delay_seconds)
                status, body, headers = owner.routes.get(self.path, (404, "missing", {}))
                payload = body.encode()
                self.send_response(status)
                for key, value in headers.items():
                    self.send_header(key, value)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, *_args):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    @property
    def origin(self) -> str:
        host, port = self.server.server_address
        return f"http://{host}:{port}"

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *_args):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)


@unittest.skipIf(CrawleeEngine is None, "Crawlee is an optional dependency")
class CrawleeEngineTests(unittest.IsolatedAsyncioTestCase):
    async def collect(self, spec: RunSpec, work: Path, *, allow_local: bool = False):
        if allow_local:
            spec.allow_local = True
        pages: list[PageEvidence] = []
        report = await CrawleeEngine().collect(spec, pages.append, work_dir=work)
        return report, pages

    async def test_duplicate_links_are_saved_once_and_depth_is_bounded(self):
        with Site({
            "/": (200, '<a href="/one">one</a><a href="/one#part">duplicate</a>', {}),
            "/one": (200, '<a href="/two">two</a>', {}),
            "/two": (200, "end", {}),
            "/robots.txt": (200, "User-agent: *\nAllow: /", {}),
        }) as site, TemporaryDirectory() as temp:
            report, pages = await self.collect(RunSpec([site.origin + "/"], max_depth=1), Path(temp), allow_local=True)
            self.assertEqual({page.url for page in pages}, {site.origin + "/", site.origin + "/one"})
            self.assertEqual({page.depth for page in pages}, {0, 1})
            self.assertEqual(site.hits["/one"], 1)
            self.assertEqual(site.hits["/two"], 0)
            self.assertEqual(report.pages_saved, 2)

    async def test_page_cap_stops_link_discovery(self):
        with Site({
            "/": (200, '<a href="/a">a</a><a href="/b">b</a>', {}),
            "/a": (200, "a", {}), "/b": (200, "b", {}),
            "/robots.txt": (200, "User-agent: *\nAllow: /", {}),
        }) as site, TemporaryDirectory() as temp:
            report, pages = await self.collect(RunSpec([site.origin + "/"], max_pages=1), Path(temp), allow_local=True)
            self.assertEqual(len(pages), 1)
            self.assertTrue(report.limit_reached)
            self.assertEqual(site.hits["/a"] + site.hits["/b"], 0)

    async def test_external_links_and_redirects_are_candidates_and_never_followed(self):
        with Site({"/linked": (200, "should not hit", {}), "/redirected": (200, "should not hit", {})}) as foreign, Site({
            "/": (200, f'<a href="{foreign.origin}/linked">external</a>', {}),
            "/jump": (302, "", {"Location": foreign.origin + "/redirected"}),
            "/robots.txt": (200, "User-agent: *\nAllow: /", {}),
        }) as site, TemporaryDirectory() as temp:
            report, pages = await self.collect(RunSpec([site.origin + "/", site.origin + "/jump"]), Path(temp), allow_local=True)
            self.assertEqual(len(pages), 2)
            self.assertIn(foreign.origin + "/linked", report.candidates)
            self.assertIn(foreign.origin + "/redirected", report.candidates)
            self.assertEqual(foreign.hits["/linked"] + foreign.hits["/redirected"], 0)
            jump = next(page for page in pages if page.url.endswith("/jump"))
            self.assertEqual(jump.status_code, 302)

    async def test_same_origin_redirect_location_is_queued_at_next_depth(self):
        with Site({
            "/jump": (302, "", {"Location": "/destination#section"}),
            "/destination": (200, "destination", {}),
            "/robots.txt": (200, "User-agent: *\nAllow: /", {}),
        }) as site, TemporaryDirectory() as temp:
            report, pages = await self.collect(RunSpec([site.origin + "/jump"], max_depth=1), Path(temp), allow_local=True)
            by_path = {page.url.removeprefix(site.origin): page for page in pages}
            self.assertEqual(by_path["/jump"].status_code, 302)
            self.assertEqual(by_path["/jump"].depth, 0)
            self.assertEqual(by_path["/destination"].depth, 1)
            self.assertEqual(site.hits["/destination"], 1)
            self.assertEqual(report.pages_saved, 2)

    async def test_loopback_is_denied_by_default(self):
        with Site({"/": (200, "secret", {})}) as site, TemporaryDirectory() as temp:
            report, pages = await self.collect(RunSpec([site.origin + "/"]), Path(temp))
            self.assertEqual(pages, [])
            self.assertGreaterEqual(report.failed_requests, 1)
            self.assertEqual(site.hits["/"], 0)

    async def test_robots_disallowed_seed_is_reported_as_failure(self):
        with Site({
            "/blocked": (200, "must not fetch", {}),
            "/robots.txt": (200, "User-agent: *\nDisallow: /blocked", {}),
        }) as site, TemporaryDirectory() as temp:
            report, pages = await self.collect(RunSpec([site.origin + "/blocked"]), Path(temp), allow_local=True)
            self.assertEqual(pages, [])
            self.assertEqual(report.pages_saved, 0)
            self.assertEqual(report.failed_requests, 1)
            self.assertEqual(
                report.failures,
                [{"url": site.origin + "/blocked", "reason": "robots_disallowed"}],
            )
            self.assertEqual(site.hits["/blocked"], 0)

    async def test_callback_failure_stops_before_following_links_and_reraises(self):
        with Site({
            "/": (200, '<a href="/later">later</a>', {}),
            "/later": (200, "must not fetch", {}),
            "/robots.txt": (200, "User-agent: *\nAllow: /", {}),
        }) as site, TemporaryDirectory() as temp:
            expected = RuntimeError("storage sink is unavailable")
            callback_calls = 0

            def fail_sink(_evidence):
                nonlocal callback_calls
                callback_calls += 1
                raise expected

            spec = RunSpec([site.origin + "/"])
            spec.allow_local = True
            with self.assertRaises(RuntimeError) as raised:
                await CrawleeEngine().collect(
                    spec, fail_sink, work_dir=Path(temp)
                )
            self.assertIs(raised.exception, expected)
            self.assertEqual(callback_calls, 1)
            self.assertEqual(site.hits["/later"], 0)

    async def test_wait_for_timeout_cancels_inflight_crawlee_request(self):
        with Site({
            "/slow": (200, "slow", {}),
            "/robots.txt": (200, "User-agent: *\nAllow: /", {}),
        }, slow_paths={"/slow"}, delay_seconds=1.5) as site, TemporaryDirectory() as temp:
            spec = RunSpec([site.origin + "/slow"], timeout_seconds=10)
            spec.allow_local = True
            with self.assertRaises(asyncio.TimeoutError):
                await asyncio.wait_for(
                    CrawleeEngine().collect(spec, lambda _page: None, work_dir=Path(temp)),
                    timeout=0.2,
                )
            self.assertEqual(site.hits["/slow"], 1)

    async def test_task_cancel_is_not_converted_to_success(self):
        with Site({
            "/slow": (200, "slow", {}),
            "/robots.txt": (200, "User-agent: *\nAllow: /", {}),
        }, slow_paths={"/slow"}, delay_seconds=1.5) as site, TemporaryDirectory() as temp:
            spec = RunSpec([site.origin + "/slow"], timeout_seconds=10)
            spec.allow_local = True
            task = asyncio.create_task(
                CrawleeEngine().collect(spec, lambda _page: None, work_dir=Path(temp))
            )
            for _ in range(30):
                if site.hits["/slow"]:
                    break
                await asyncio.sleep(0.02)
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
            self.assertEqual(site.hits["/slow"], 1)

    async def test_tcp_connect_uses_validated_ip_and_revalidates_dns_answers(self):
        backend = _ScopedAnyIOBackend({("jobs.example", 443)}, allow_local=False)
        connected_hosts: list[str] = []

        def address(ip: str):
            return [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", (ip, 443))]

        async def block_external_connect(_backend, *, host, **_kwargs):
            connected_hosts.append(host)
            raise OSError("test blocks external network access")

        with patch("jevscout.adapters.crawling.crawlee.socket.getaddrinfo", side_effect=[address("93.184.216.34"), address("127.0.0.1")]), patch.object(
            httpcore2.AnyIOBackend, "connect_tcp", block_external_connect
        ):
            with self.assertRaisesRegex(OSError, "test blocks external network access"):
                await backend.connect_tcp("jobs.example", 443)
            with self.assertRaisesRegex(OSError, "non-public address"):
                await backend.connect_tcp("jobs.example", 443)

        self.assertEqual(connected_hosts, ["93.184.216.34"])

    async def test_allow_local_accepts_loopback_fixture(self):
        with Site({"/": (200, "local", {}), "/robots.txt": (200, "User-agent: *\nAllow: /", {})}) as site, TemporaryDirectory() as temp:
            spec = RunSpec([site.origin + "/"])
            spec.allow_local = True
            report, pages = await self.collect(spec, Path(temp))
            self.assertEqual(report.pages_saved, 1)
            self.assertEqual(pages[0].html, "local")

    async def test_503_retries_once_then_reports_failure(self):
        with Site({"/busy": (503, "busy", {}), "/robots.txt": (200, "User-agent: *\nAllow: /", {})}) as site, TemporaryDirectory() as temp:
            report, pages = await self.collect(RunSpec([site.origin + "/busy"]), Path(temp), allow_local=True)
            self.assertEqual(pages, [])
            self.assertEqual(site.hits["/busy"], 2)
            self.assertEqual(report.failed_requests, 1)
            self.assertEqual(
                report.failures,
                [{"url": site.origin + "/busy", "reason": "request_failed", "attempts": 2}],
            )


if __name__ == "__main__":
    unittest.main()
