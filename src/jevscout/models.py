"""Small persisted run records used by the filesystem store."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlsplit


def _validate_seed_url(url: object) -> None:
    if (
        not isinstance(url, str)
        or not url
        or any(char.isspace() or ord(char) < 32 or ord(char) == 127 or char == "\\" for char in url)
    ):
        raise ValueError("seed URLs must be non-empty HTTP(S) URLs")
    try:
        parsed = urlsplit(url)
        if parsed.scheme.lower() not in {"http", "https"}:
            raise ValueError("seed URLs must be non-empty HTTP(S) URLs")
        hostname = parsed.hostname
        parsed.port  # Access validates malformed and out-of-range ports.
    except ValueError as exc:
        raise ValueError("seed URLs must be valid HTTP(S) URLs") from exc
    if not hostname or parsed.username is not None or parsed.password is not None:
        raise ValueError("seed URLs must have a host and must not include credentials")


@dataclass
class RunSpec:
    seed_urls: list[str]
    max_pages: int = 10
    max_depth: int = 1
    timeout_seconds: int = 60

    def __post_init__(self) -> None:
        if not isinstance(self.seed_urls, list) or not self.seed_urls:
            raise ValueError("seed_urls must be a non-empty list")
        for url in self.seed_urls:
            _validate_seed_url(url)
        if isinstance(self.max_pages, bool) or not isinstance(self.max_pages, int) or not 1 <= self.max_pages <= 1000:
            raise ValueError("max_pages must be between 1 and 1000")
        if isinstance(self.max_depth, bool) or not isinstance(self.max_depth, int) or not 0 <= self.max_depth <= 10:
            raise ValueError("max_depth must be between 0 and 10")
        if (
            isinstance(self.timeout_seconds, bool)
            or not isinstance(self.timeout_seconds, int)
            or not 1 <= self.timeout_seconds <= 3600
        ):
            raise ValueError("timeout_seconds must be between 1 and 3600")

    def to_dict(self) -> dict[str, Any]:
        return {
            "seed_urls": list(self.seed_urls),
            "max_pages": self.max_pages,
            "max_depth": self.max_depth,
            "timeout_seconds": self.timeout_seconds,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "RunSpec":
        if not isinstance(payload, dict):
            raise TypeError("run spec must be an object")
        allowed = {"seed_urls", "max_pages", "max_depth", "timeout_seconds"}
        unknown = payload.keys() - allowed
        if unknown:
            raise ValueError(f"unknown run spec fields: {', '.join(sorted(unknown))}")
        return cls(**payload)


@dataclass
class RunRecord:
    id: str
    spec: RunSpec
    status: str = "pending"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"))
    error: str | None = None

    def __post_init__(self) -> None:
        if self.status not in {"pending", "running", "completed", "partial", "failed", "cancelled"}:
            raise ValueError("invalid run status")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "spec": self.spec.to_dict(),
            "status": self.status,
            "created_at": self.created_at,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "RunRecord":
        if not isinstance(payload, dict):
            raise TypeError("run record must be an object")
        allowed = {"id", "spec", "status", "created_at", "error"}
        unknown = payload.keys() - allowed
        if unknown:
            raise ValueError(f"unknown run record fields: {', '.join(sorted(unknown))}")
        values = dict(payload)
        values["spec"] = RunSpec.from_dict(values["spec"])
        return cls(**values)
