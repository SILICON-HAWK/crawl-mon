"""Explicitly started, low-frequency refresh of a small fixed set of public feeds."""
from __future__ import annotations

import argparse
import asyncio
import fcntl
import json
import os
import signal
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from jevscout.core.models import RunSpec
from jevscout.storage.filesystem import FileRunStore
from jevscout.application.operations import execute_run

FEEDS = {
    'remoteok': 'https://remoteok.com/api?tag=dev',
    'sonicwall': 'https://boards-api.greenhouse.io/v1/boards/sonicwall/jobs?content=true',
    'firstwork': 'https://api.ashbyhq.com/posting-api/job-board/firstwork?includeCompensation=true',
    'transperfect': 'https://transperfect.recruitee.com/api/offers/',
    'nexthire': 'https://nexthire.breezy.hr/json',
}
SUCCESS_INTERVAL = 12 * 3600
FAILURE_INTERVAL = 24 * 3600
BETWEEN_FEEDS = 60


def next_attempt_at(attempted_at: float, status: str) -> float:
    return attempted_at + (SUCCESS_INTERVAL if status == 'completed' else FAILURE_INTERVAL)


def historical_due_at(now: float, last_attempt: float | None, status: str | None, persisted: float | None) -> float:
    historical = next_attempt_at(last_attempt, status or 'failed') if last_attempt is not None else now
    return max(historical, persisted) if persisted is not None else historical


def _write(path: Path, document: dict) -> None:
    name = None
    try:
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=path.parent, delete=False, prefix='.refresh-') as out:
            name = out.name
            json.dump(document, out, ensure_ascii=False, sort_keys=True, allow_nan=False)
            out.write('\n'); out.flush(); os.fsync(out.fileno())
        os.replace(name, path)
    finally:
        if name and os.path.exists(name): os.unlink(name)


def _latest_runs(store: FileRunStore) -> dict[str, tuple[float, str]]:
    found = {}
    for record in store.list_runs():
        for name, url in FEEDS.items():
            if record.spec.seed_urls != [url]: continue
            try:
                created = datetime.fromisoformat(record.created_at.replace('Z', '+00:00')).timestamp()
            except (ValueError, AttributeError):
                continue
            if name not in found or created > found[name][0]: found[name] = (created, record.status)
    return found


def run_worker(root: Path, stop: threading.Event) -> None:
    from jevscout.adapters.crawling.crawlee import CrawleeEngine
    root = root.resolve()
    store = FileRunStore(root)
    directory = root / 'feed-refresh'
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    lock = (directory / 'worker.lock').open('a+b')
    try:
        try: fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError: raise RuntimeError('a feed refresh worker is already running') from None
        state_path = directory / 'state.json'
        if state_path.exists():
            state = json.loads(state_path.read_text(encoding='utf-8'))
            if not isinstance(state, dict) or not isinstance(state.get('feeds'), dict):
                raise ValueError('invalid refresh state; refusing to start')
        else:
            state = {'version': 1, 'feeds': {}, 'next_global_at': 0}
        history = _latest_runs(store)
        now = time.time()
        for name in FEEDS:
            item = state['feeds'].setdefault(name, {})
            prior = history.get(name)
            item['next_attempt_at'] = historical_due_at(now, prior[0] if prior else None,
                                                          prior[1] if prior else None,
                                                          item.get('next_attempt_at'))
        state.update(status='running', pid=os.getpid())
        _write(state_path, state)
        engine = CrawleeEngine(minimum_request_interval=2, max_retries=0, respect_crawl_delay=True)
        stop_path = directory / 'stop.request'
        while not stop.is_set() and not stop_path.exists():
            name = min(FEEDS, key=lambda n: state['feeds'][n]['next_attempt_at'])
            item = state['feeds'][name]
            now = time.time()
            due = max(item['next_attempt_at'], state.get('next_global_at', 0))
            if due > now:
                stop.wait(min(due - now, 5)); continue
            # Reserve a full failure interval before touching the network, including on process crash.
            item.update(last_attempt_at=now, next_attempt_at=now + FAILURE_INTERVAL, status='starting')
            state['next_global_at'] = now + BETWEEN_FEEDS
            _write(state_path, state)
            try:
                record = store.create(RunSpec([FEEDS[name]], max_pages=1, max_depth=0,
                                              timeout_seconds=120, allow_local=False))
                item.update(run_id=record.id, status='running'); _write(state_path, state)
                finished = asyncio.run(execute_run(store, record.id, approved=True, engine=engine))
                status = finished.status
                item.update(status=status, next_attempt_at=next_attempt_at(now, status))
            except Exception:
                item['status'] = 'failed'
            item['finished_at'] = time.time()
            _write(state_path, state)
            print(f'feed={name} status={item["status"]}', flush=True)
        state['status'] = 'stopped'; _write(state_path, state)
        stop_path.unlink(missing_ok=True)
    finally:
        fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
        lock.close()


def _worker_running(directory: Path) -> bool:
    path = directory / 'worker.lock'
    if not path.exists():
        return False
    with path.open('a+b') as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return True
        fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description='Refresh known public feeds at a conservative rate')
    parser.add_argument('--data-dir', type=Path, default=Path('data'))
    parser.add_argument('--approve', action='store_true', help='authorize ongoing scheduled network requests')
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument('--status', action='store_true', help='show saved schedule and whether a worker holds the lock')
    actions.add_argument('--stop', action='store_true', help='request a graceful stop of the worker')
    args = parser.parse_args()
    directory = args.data_dir.resolve() / 'feed-refresh'
    if args.status:
        path = directory / 'state.json'
        state = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'status':'not_started'}
        state['worker_running'] = _worker_running(directory)
        print(json.dumps(state, indent=2, sort_keys=True))
        return
    if args.stop:
        if not _worker_running(directory):
            print('No feed refresh worker is running.')
            return
        (directory / 'stop.request').touch(mode=0o600)
        print('Stop requested; the current bounded request may finish first.')
        return
    if not args.approve: parser.error('ongoing refresh requires --approve')
    stop = threading.Event()
    for sig in (signal.SIGINT, signal.SIGTERM): signal.signal(sig, lambda *_: stop.set())
    run_worker(args.data_dir, stop)


if __name__ == '__main__': main()
