"""Bounded Crawlee HTTP collection behind the application engine contract."""

from __future__ import annotations

import asyncio
import ipaddress
import logging
import signal
import socket
import threading
from urllib.robotparser import RobotFileParser
from contextlib import asynccontextmanager, contextmanager
from datetime import timedelta
from pathlib import Path
from typing import Callable
from urllib.parse import urldefrag, urljoin, urlsplit

import httpcore2
import httpx2
from crawlee import ConcurrencySettings, Request
from crawlee.configuration import Configuration
from crawlee.crawlers import BeautifulSoupCrawler
from crawlee.events import EventManager
from crawlee.http_clients import HttpxHttpClient
from crawlee.storage_clients import FileSystemStorageClient

from jevscout.core.engine import CollectionReport, PageEvidence
from jevscout.core.models import RunSpec


@contextmanager
def _quiet_framework_loggers():
    """Keep framework diagnostics from writing raw request URLs to application logs."""
    root = logging.Logger.manager.loggerDict
    names = {"crawlee", "httpx2", "httpcore2"}
    names.update(name for name in root if name.startswith(("crawlee.", "httpx2.", "httpcore2.")))
    loggers = {name: logging.getLogger(name) for name in names}
    previous = {name: logger.level for name, logger in loggers.items()}
    try:
        for logger in loggers.values():
            logger.setLevel(logging.CRITICAL)
        yield
    finally:
        for name, level in previous.items():
            loggers[name].setLevel(level)


def _origin(url: str) -> tuple[str, str, int] | None:
    try:
        parsed = urlsplit(url)
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
            return None
        if parsed.username is not None or parsed.password is not None:
            return None
        port = parsed.port or (443 if parsed.scheme.lower() == "https" else 80)
        return parsed.scheme.lower(), parsed.hostname.lower(), port
    except ValueError:
        return None


def _clean_http_url(url: str) -> str | None:
    if not isinstance(url, str) or any(ord(char) < 32 or char.isspace() or char == "\\" for char in url):
        return None
    clean, _fragment = urldefrag(url)
    if _origin(clean) is None:
        return None
    return clean


async def _guard_request(request: httpx2.Request, *, origins: set[tuple[str, str, int]]) -> None:
    """Validate the requested origin before it reaches the connection pool."""
    url = str(request.url)
    origin = _origin(url)
    if origin is None or origin not in origins:
        raise PermissionError("request target is outside the approved crawl origin")


class _ScopedAnyIOBackend(httpcore2.AnyIOBackend):
    """Resolve and validate peers at the last HTTPcore connection boundary.

    The adapter pins this backend into Crawlee's HttpxHttpClient transport pool. It
    resolves each TCP connection once, validates every returned address, then asks
    AnyIO to connect to a selected numeric address. HTTPcore retains the original
    URL origin for Host headers and TLS SNI.
    """

    def __init__(self, endpoints: set[tuple[str, int]], *, allow_local: bool) -> None:
        self._endpoints = endpoints
        self._allow_local = allow_local

    async def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,
        local_address: str | None = None,
        socket_options=None,
    ):
        if (host.lower(), port) not in self._endpoints:
            raise OSError("TCP endpoint is outside the approved crawl origins")
        try:
            addresses = await asyncio.to_thread(
                socket.getaddrinfo, host, port, 0, socket.SOCK_STREAM
            )
        except OSError as exc:
            raise OSError("request host could not be safely resolved") from exc
        if not addresses:
            raise OSError("request host resolved to no addresses")

        validated: list[str] = []
        for address in addresses:
            ip = ipaddress.ip_address(address[4][0].split("%", 1)[0])
            if ip.is_global or (self._allow_local and ip.is_loopback):
                validated.append(str(ip))
            else:
                raise OSError("request host resolved to a non-public address")

        # Connect using the validated IP, so a second DNS lookup cannot change the peer.
        numeric_host = validated[0]
        return await super().connect_tcp(
            host=numeric_host,
            port=port,
            timeout=timeout,
            local_address=local_address,
            socket_options=socket_options,
        )


class _ScopedHttpxHttpClient(HttpxHttpClient):
    """Install the scoped TCP backend in Crawlee's pinned httpx2 transport."""

    def __init__(self, *, network_backend: _ScopedAnyIOBackend, **kwargs) -> None:
        self._scoped_network_backend = network_backend
        super().__init__(**kwargs)

    def _get_client(self, proxy_url: str | None) -> httpx2.AsyncClient:
        if proxy_url is not None or self._proxy is not None:
            raise RuntimeError("HTTP proxies are not supported by the scoped crawl engine")
        client = super()._get_client(proxy_url)
        transport = getattr(client, "_transport", None)
        pool = getattr(transport, "_pool", None)
        if not isinstance(pool, httpcore2.AsyncConnectionPool) or not hasattr(pool, "_network_backend"):
            raise RuntimeError("unsupported httpx2/httpcore2 transport layout for scoped networking")
        pool._network_backend = self._scoped_network_backend
        return client


def _sigint_context(owning_task: asyncio.Task):
    """Make SIGINT cancel the application task; Crawlee otherwise consumes it as a pause."""

    @asynccontextmanager
    async def context():
        if threading.current_thread() is not threading.main_thread():
            yield
            return

        loop = asyncio.get_running_loop()
        try:
            # Crawlee installs its own handler before entering additional context managers.
            # Its run() finally block removes this replacement when the crawl exits.
            loop.add_signal_handler(signal.SIGINT, owning_task.cancel)
        except NotImplementedError:
            previous = signal.signal(
                signal.SIGINT,
                lambda *_args: loop.call_soon_threadsafe(owning_task.cancel),
            )
            try:
                yield
            finally:
                signal.signal(signal.SIGINT, previous)
            return

        yield

    return context()


class CrawleeEngine:
    """Collect pages using Crawlee's request frontier, deduplication, and retries."""

    name = "crawlee"
    version = "1.11.0"

    def __init__(self, *, minimum_request_interval: float = 0, max_retries: int = 1,
                 respect_crawl_delay: bool = False):
        if minimum_request_interval < 0 or max_retries < 0:
            raise ValueError("invalid crawler rate settings")
        self.minimum_request_interval = minimum_request_interval
        self.max_retries = max_retries
        self.respect_crawl_delay = respect_crawl_delay

    async def collect(
        self,
        spec: RunSpec,
        on_page: Callable[[PageEvidence], None],
        *,
        work_dir: Path,
    ) -> CollectionReport:
        report = CollectionReport()
        owning_task = asyncio.current_task()
        if owning_task is None:
            raise RuntimeError("Crawlee collection requires an asyncio task")
        allowed_origins = {_origin(seed) for seed in spec.seed_urls}
        origins = {origin for origin in allowed_origins if origin is not None}
        allow_local = bool(getattr(spec, "allow_local", False))
        callback_error: Exception | None = None
        quiet_logger = logging.Logger("jevscout.crawlee", level=logging.CRITICAL)
        quiet_logger.disabled = True
        crawler: BeautifulSoupCrawler
        endpoints = {(host, port) for _scheme, host, port in origins}
        network_backend = _ScopedAnyIOBackend(endpoints, allow_local=allow_local)

        def stop_if_cancelled() -> None:
            if owning_task.cancelling():
                crawler.stop(reason="Application collection task was cancelled.")
                raise asyncio.CancelledError

        request_times: dict[tuple[str, str, int], float] = {}
        crawl_delays: dict[tuple[str, str, int], float] = {}

        async def request_guard(request: httpx2.Request) -> None:
            stop_if_cancelled()
            await _guard_request(request, origins=origins)
            origin = _origin(str(request.url))
            if origin is not None:
                loop = asyncio.get_running_loop()
                interval = max(self.minimum_request_interval, crawl_delays.get(origin, 0))
                remaining = request_times.get(origin, 0) + interval - loop.time()
                if remaining > 0:
                    await asyncio.sleep(remaining)
                stop_if_cancelled()
                request_times[origin] = loop.time()

        async def inspect_robots(response: httpx2.Response) -> None:
            if not self.respect_crawl_delay or response.request.url.path != "/robots.txt" or response.status_code != 200:
                return
            body = await response.aread()
            parser = RobotFileParser()
            parser.parse(body.decode("utf-8", errors="replace").splitlines())
            agent = response.request.headers.get("user-agent", "*")
            delay = parser.crawl_delay(agent)
            if delay is None:
                delay = parser.crawl_delay("*")
            origin = _origin(str(response.request.url))
            if origin is not None and delay is not None:
                crawl_delays[origin] = max(0, delay)

        client = _ScopedHttpxHttpClient(
            network_backend=network_backend,
            persist_cookies_per_session=False,
            follow_redirects=False,
            trust_env=False,
            timeout=min(max(spec.timeout_seconds, 1), 30),
            event_hooks={"request": [request_guard], "response": [inspect_robots]},
        )
        crawler = BeautifulSoupCrawler(
            configuration=Configuration(
                storage_dir=str((work_dir / "crawlee").resolve()),
                purge_on_start=True,
                log_level="CRITICAL",
            ),
            event_manager=EventManager(),
            storage_client=FileSystemStorageClient(),
            http_client=client,
            concurrency_settings=ConcurrencySettings(
                min_concurrency=1, max_concurrency=1, desired_concurrency=1
            ),
            max_crawl_depth=spec.max_depth,
            max_requests_per_crawl=spec.max_pages,
            max_request_retries=self.max_retries,
            max_session_rotations=0,
            use_session_pool=False,
            respect_robots_txt_file=True,
            request_handler_timeout=timedelta(seconds=min(max(spec.timeout_seconds, 1), 30)),
            navigation_timeout=timedelta(seconds=min(max(spec.timeout_seconds, 1), 30)),
            abort_on_error=False,
            configure_logging=False,
            _logger=quiet_logger,
            _additional_context_managers=[_sigint_context(owning_task)],
        )

        @crawler.router.default_handler
        async def handle_page(context) -> None:
            nonlocal callback_error
            stop_if_cancelled()
            depth = int(context.request.user_data.get("jevscout_depth", 0))
            response = context.http_response
            body = await response.read()
            loaded_url = context.request.loaded_url or context.request.url
            evidence = PageEvidence(
                url=loaded_url,
                html=body.decode("utf-8", errors="replace"),
                status_code=response.status_code,
                depth=depth,
            )
            try:
                on_page(evidence)
            except Exception as exc:
                callback_error = exc
                crawler.stop(reason="Page evidence callback failed.")
                raise
            stop_if_cancelled()
            report.pages_saved += 1

            for anchor in context.soup.select("a[href]"):
                target = _clean_http_url(urljoin(loaded_url, anchor.get("href", "")))
                if target is not None and _origin(target) != _origin(context.request.url):
                    report.candidates.append(target)

            # Crawlee extracts and filters links, and owns their queue and deduplication.
            # The transform adds application depth metadata to each queued request.
            def tag_depth(options):
                target = _clean_http_url(options["url"])
                if target is None:
                    return "skip"
                if _origin(target) != _origin(context.request.url):
                    report.candidates.append(target)
                    return "skip"
                options["url"] = target
                options["user_data"] = {**options.get("user_data", {}), "jevscout_depth": depth + 1}
                return options

            if depth < spec.max_depth and report.pages_saved < spec.max_pages:
                await context.enqueue_links(strategy="same-origin", transform_request_function=tag_depth)

            # An out-of-origin Location is evidence only. Same-origin redirects are
            # discovered as ordinary queued requests and are never followed inline.
            location = response.headers.get("location")
            if location:
                target = _clean_http_url(urljoin(loaded_url, location))
                if target is not None:
                    if _origin(target) == _origin(context.request.url):
                        if depth < spec.max_depth and report.pages_saved < spec.max_pages:
                            await context.enqueue_links(
                                requests=[Request.from_url(target, user_data={"jevscout_depth": depth + 1})],
                                strategy="same-origin",
                            )
                    else:
                        report.candidates.append(target)

        @crawler.failed_request_handler
        async def failed(context, _error) -> None:
            report.failed_requests += 1
            report.failures.append(
                {
                    "url": _clean_http_url(context.request.url),
                    "reason": "request_failed",
                    "attempts": context.request.retry_count + 1,
                }
            )

        @crawler.on_skipped_request
        async def skipped(url: str, reason: str) -> None:
            if reason == "robots_txt":
                report.failed_requests += 1
                report.failures.append(
                    {"url": _clean_http_url(url), "reason": "robots_disallowed"}
                )

        seeds = []
        for seed in spec.seed_urls[: spec.max_pages]:
            clean = _clean_http_url(seed)
            if clean is not None:
                seeds.append(Request.from_url(clean, user_data={"jevscout_depth": 0}))
        with _quiet_framework_loggers():
            await crawler.run(seeds)
        if owning_task.cancelling():
            raise asyncio.CancelledError
        if callback_error is not None:
            raise callback_error
        report.limit_reached = report.pages_saved >= spec.max_pages
        # Preserve first-seen ordering while avoiding repeated candidate reporting.
        report.candidates = list(dict.fromkeys(report.candidates))
        return report
