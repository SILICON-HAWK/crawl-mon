"""Explicit, bounded checks of saved job listing URLs.

The default transport follows the same DNS pinning and origin guard as the
scoped Crawlee adapter. Redirects are disabled: a redirect is a result to
inspect, never permission to contact another host.
"""

from __future__ import annotations

import asyncio
import fcntl
import json
import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable
from urllib.parse import urlsplit


def _validate_url(url: object) -> tuple[str, str, int]:
    if not isinstance(url, str) or not url or len(url) > 8192 or url != url.strip() or any(
        ord(ch) < 32 or ord(ch) == 127 or ch.isspace() or ch == "\\" for ch in url
    ):
        raise ValueError("invalid listing URL")
    try:
        parsed = urlsplit(url)
        scheme = parsed.scheme.lower()
        host = parsed.hostname
        port = parsed.port or (443 if scheme == "https" else 80)
    except ValueError:
        raise ValueError("invalid listing URL") from None
    if scheme not in {"http", "https"} or not host or parsed.username is not None or parsed.password is not None:
        raise ValueError("invalid listing URL")
    return scheme, host.lower(), port


@dataclass(frozen=True)
class AvailabilityCheck:
    url: str
    state: str
    status_code: int | None
    checked_at: str
    reason: str | None = None

    def __post_init__(self) -> None:
        if self.state not in {"available", "unavailable", "unknown"}:
            raise ValueError("invalid availability state")

    def to_dict(self) -> dict:
        return asdict(self)


class AvailabilityStore:
    """Store latest checks independently from job decisions and run artifacts."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)

    def _locked(self):
        lock_path = self.path.with_name(f".{self.path.name}.lock")
        if lock_path.is_symlink():
            raise ValueError("invalid availability lock")
        return lock_path.open("a+b")

    def read(self) -> dict[str, AvailabilityCheck]:
        if not self.path.exists():
            return {}
        if self.path.is_symlink() or not self.path.is_file():
            raise ValueError("invalid availability storage")
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("invalid availability document")
        result = {}
        for url, item in payload.items():
            if not isinstance(item, dict):
                raise ValueError("invalid availability document")
            record = AvailabilityCheck(**item)
            if record.url != url:
                raise ValueError("invalid availability document")
            result[url] = record
        return result

    def put(self, checks: Iterable[AvailabilityCheck]) -> dict[str, AvailabilityCheck]:
        with self._locked() as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            records = self.read()
            for check in checks:
                records[check.url] = check
            self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            name = None
            try:
                with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=self.path.parent,
                                                 prefix=".availability-", delete=False) as handle:
                    name = handle.name
                    json.dump({key: value.to_dict() for key, value in records.items()}, handle,
                              ensure_ascii=False, sort_keys=True, allow_nan=False)
                    handle.write("\n")
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(name, self.path)
            finally:
                if name is not None and os.path.exists(name):
                    os.unlink(name)
            return records


class AvailabilityChecker:
    """Check at most 100 explicitly supplied URLs in a caller initiated operation.

    Inject `requester` for controlled fixtures; it receives a URL and returns
    `(status_code, redirect_location)`. The default transport never uses proxies
    or follows redirects and rejects any DNS answer that is not globally routed.
    """

    MAX_URLS = 100

    def __init__(self, store: AvailabilityStore, requester: Callable | None = None,
                 *, _allow_local_for_test: bool = False):
        self.store = store
        self.requester = requester
        self._allow_local_for_test = _allow_local_for_test

    async def check(self, urls: Iterable[str], *, requested: bool = False) -> list[AvailabilityCheck]:
        if requested is not True:
            raise PermissionError("availability checks require an explicit user request")
        targets = list(urls)
        if not targets or len(targets) > self.MAX_URLS:
            raise ValueError("provide between 1 and 100 listing URLs")
        checked = []
        for url in targets:
            try:
                _validate_url(url)
            except ValueError:
                raise
            now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            try:
                operation = self.requester(url) if self.requester else self._request(url)
                status, location = await asyncio.wait_for(operation, timeout=15)
                if isinstance(status, bool) or not isinstance(status, int) or not 100 <= status <= 599:
                    raise ValueError("invalid HTTP response status")
                if status == 200:
                    item = AvailabilityCheck(url, "available", status, now)
                elif status in {404, 410}:
                    item = AvailabilityCheck(url, "unavailable", status, now, "listing_not_found")
                else:
                    reason = "redirect_not_followed" if 300 <= status < 400 else "inconclusive_http_status"
                    item = AvailabilityCheck(url, "unknown", status, now, reason)
            except Exception as exc:
                item = AvailabilityCheck(url, "unknown", None, now, _safe_reason(exc))
            checked.append(item)
            # Persist after each URL so cancellation or process failure preserves completed work.
            self.store.put([item])
        return checked

    async def _request(self, url: str) -> tuple[int, str | None]:
        try:
            import httpcore2
            import httpx2
            from jevscout.adapters.crawling.crawlee import _ScopedAnyIOBackend, _ScopedHttpxHttpClient, _origin
        except ImportError as exc:
            raise RuntimeError("scoped HTTP dependencies are unavailable") from exc
        origin = _origin(url)
        if origin is None:
            raise ValueError("invalid listing URL")
        scheme, host, port = origin
        backend = _ScopedAnyIOBackend({(host, port)}, allow_local=self._allow_local_for_test)
        async def guard(request):
            if _origin(str(request.url)) != origin:
                raise PermissionError("request target is outside the checked origin")
        client = _ScopedHttpxHttpClient(network_backend=backend, persist_cookies_per_session=False,
                                        follow_redirects=False, trust_env=False, timeout=15,
                                        event_hooks={"request": [guard]})
        http_client = client._get_client(None)
        try:
            response = await http_client.get(url, follow_redirects=False)
            return response.status_code, response.headers.get("location")
        finally:
            await http_client.aclose()


def _safe_reason(exc: Exception) -> str:
    if isinstance(exc, (TimeoutError, asyncio.TimeoutError)):
        return "timeout"
    if isinstance(exc, PermissionError):
        return "scope_rejected"
    if isinstance(exc, ValueError):
        return "invalid_response"
    # Do not persist exception messages, which can contain sensitive URLs.
    return "request_failed"

class AvailabilityManager:
    """Single explicit background check, bounded and shared across local processes."""
    def __init__(self, store: AvailabilityStore):
        import threading
        self.store = store
        self._mutex = threading.Lock()
        self._state = {'status': 'idle', 'total': 0, 'completed': 0}

    def status(self):
        with self._mutex:
            return dict(self._state)

    def start(self, urls: list[str]):
        import fcntl
        import threading
        if not isinstance(urls, list) or not urls or len(urls) > AvailabilityChecker.MAX_URLS:
            raise ValueError('provide between 1 and 100 listing URLs')
        for url in urls:
            _validate_url(url)
        urls = list(dict.fromkeys(urls))
        lock = (self.store.path.parent / '.availability-run.lock').open('a+b')
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            lock.close()
            raise RuntimeError('availability check already running') from None
        with self._mutex:
            self._state = {'status':'running','total':len(urls),'completed':0}
        def work():
            try:
                async def execute():
                    checker = AvailabilityChecker(self.store)
                    for url in urls:
                        await checker.check([url], requested=True)
                        with self._mutex:
                            self._state['completed'] += 1
                        await asyncio.sleep(1)
                asyncio.run(execute())
                with self._mutex:
                    self._state['status'] = 'completed'
            except Exception:
                with self._mutex:
                    self._state['status'] = 'failed'
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
                lock.close()
        try:
            threading.Thread(target=work, daemon=True, name='listing-availability').start()
        except Exception:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
            lock.close()
            with self._mutex: self._state['status'] = 'failed'
            raise
        return self.status()
