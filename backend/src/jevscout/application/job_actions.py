"""Local JSON persistence for per-user job decisions."""

from __future__ import annotations

import fcntl
import json
import os
import re
import tempfile
from pathlib import Path
from urllib.parse import urlsplit


class JobActionsStore:
    """Persist a user's URL-to-decision map independently from their profile."""

    _USERNAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
    STATUSES = frozenset({"interested", "not_interested"})

    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)

    @classmethod
    def _safe_username(cls, username: str) -> str:
        if not isinstance(username, str) or not cls._USERNAME.fullmatch(username):
            raise ValueError("invalid username")
        return username

    @staticmethod
    def validate_job_url(value: object) -> str:
        if not isinstance(value, str) or not value or len(value) > 8192:
            raise ValueError("invalid job URL")
        if value != value.strip() or any(ord(char) < 32 or ord(char) == 127 for char in value):
            raise ValueError("invalid job URL")
        try:
            parsed = urlsplit(value)
            if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
                raise ValueError("invalid job URL")
            if parsed.username is not None or parsed.password is not None:
                raise ValueError("invalid job URL")
            _ = parsed.port  # Reject malformed and out-of-range ports.
        except ValueError:
            raise ValueError("invalid job URL") from None
        return value

    def _user_dir(self, username: str) -> Path:
        safe_name = self._safe_username(username)
        path = self.root / safe_name
        resolved_root = self.root.resolve()
        resolved = path.resolve()
        if resolved.parent != resolved_root:
            raise ValueError("invalid username")
        path.mkdir(mode=0o700, exist_ok=True)
        if path.is_symlink() or path.resolve().parent != resolved_root:
            raise ValueError("invalid user directory")
        return path

    @staticmethod
    def _read(path: Path) -> dict[str, str]:
        if not path.exists():
            return {}
        if path.is_symlink() or not path.is_file():
            raise ValueError("invalid job actions storage")
        with path.open("r", encoding="utf-8") as source:
            document = json.load(source)
        if not isinstance(document, dict) or any(
            not isinstance(url, str) or status not in JobActionsStore.STATUSES
            for url, status in document.items()
        ):
            raise ValueError("invalid job actions document")
        return document

    @staticmethod
    def _atomic_write(path: Path, document: dict[str, str]) -> None:
        temporary_name = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=path.parent,
                prefix=".job-actions-", delete=False,
            ) as temporary:
                temporary_name = temporary.name
                json.dump(document, temporary, ensure_ascii=False, sort_keys=True, allow_nan=False)
                temporary.write("\n")
                temporary.flush()
                os.fsync(temporary.fileno())
            os.replace(temporary_name, path)
        finally:
            if temporary_name is not None and os.path.exists(temporary_name):
                os.unlink(temporary_name)

    def get(self, username: str) -> dict[str, str]:
        user_dir = self._user_dir(username)
        lock_path = user_dir / ".job-actions.lock"
        if lock_path.is_symlink():
            raise ValueError("invalid job actions lock")
        with lock_path.open("a+b") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            return self._read(user_dir / "job-actions.json")

    def set(self, username: str, job_url: str, status: str) -> dict[str, str]:
        self._safe_username(username)
        job_url = self.validate_job_url(job_url)
        if status not in (*self.STATUSES, "unset"):
            raise ValueError("invalid status")
        user_dir = self._user_dir(username)
        path = user_dir / "job-actions.json"
        lock_path = user_dir / ".job-actions.lock"
        if path.is_symlink() or lock_path.is_symlink():
            raise ValueError("invalid job actions storage")
        with lock_path.open("a+b") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            document = self._read(path)
            if status == "unset":
                document.pop(job_url, None)
            else:
                document[job_url] = status
            self._atomic_write(path, document)
            return document
