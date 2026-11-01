import tempfile
import unittest
import asyncio
from pathlib import Path

from jevscout.application.availability import AvailabilityChecker, AvailabilityStore


class AvailabilityTests(unittest.IsolatedAsyncioTestCase):
    async def test_classifies_statuses_and_persists_independently(self):
        async def fixture(url):
            code = {"open": 200, "gone": 410, "redirect": 302, "busy": 503}[url.rsplit("/", 1)[-1]]
            return code, "https://elsewhere.invalid/" if code == 302 else None

        with tempfile.TemporaryDirectory() as directory:
            store = AvailabilityStore(Path(directory) / "availability.json")
            checker = AvailabilityChecker(store, requester=fixture)
            records = await checker.check(
                [f"https://jobs.example/{path}" for path in ("open", "gone", "redirect", "busy")],
                requested=True,
            )
            self.assertEqual([item.state for item in records], ["available", "unavailable", "unknown", "unknown"])
            self.assertEqual([item.status_code for item in records], [200, 410, 302, 503])
            self.assertTrue(all(item.checked_at.endswith("Z") for item in records))
            self.assertEqual(store.read(), {item.url: item for item in records})

    async def test_requires_request_and_rejects_unsafe_inputs_before_request(self):
        called = False

        async def fixture(url):
            nonlocal called
            called = True
            return 200, None

        with tempfile.TemporaryDirectory() as directory:
            checker = AvailabilityChecker(AvailabilityStore(Path(directory) / "checks.json"), fixture)
            with self.assertRaises(PermissionError):
                await checker.check(["https://jobs.example/" ])
            with self.assertRaises(ValueError):
                await checker.check(["file:///etc/passwd"], requested=True)
            self.assertFalse(called)

    async def test_transport_issue_is_unknown(self):
        async def fixture(_url):
            raise OSError("network unavailable")

        with tempfile.TemporaryDirectory() as directory:
            checker = AvailabilityChecker(AvailabilityStore(Path(directory) / "checks.json"), fixture)
            [record] = await checker.check(["https://jobs.example/"], requested=True)
            self.assertEqual((record.state, record.status_code, record.reason), ("unknown", None, "request_failed"))

    async def test_real_scoped_transport_against_explicit_loopback_fixture(self):
        try:
            import crawlee  # noqa: F401
        except ImportError:
            self.skipTest("optional crawl dependencies are not installed")

        async def respond(reader, writer):
            await reader.readuntil(b"\r\n\r\n")
            writer.write(b"HTTP/1.1 200 OK\r\nContent-Length: 0\r\nConnection: close\r\n\r\n")
            await writer.drain()
            writer.close()
            await writer.wait_closed()

        server = await asyncio.start_server(respond, "127.0.0.1", 0)
        port = server.sockets[0].getsockname()[1]
        try:
            with tempfile.TemporaryDirectory() as directory:
                checker = AvailabilityChecker(
                    AvailabilityStore(Path(directory) / "checks.json"),
                    _allow_local_for_test=True,
                )
                [record] = await checker.check([f"http://127.0.0.1:{port}/listing"], requested=True)
                self.assertEqual((record.state, record.status_code), ("available", 200))
        finally:
            server.close()
            await server.wait_closed()
