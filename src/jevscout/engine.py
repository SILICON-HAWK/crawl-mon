"""Application-owned collection contracts; no crawler framework types."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Protocol

from .models import RunSpec


@dataclass(frozen=True)
class PageEvidence:
    url: str
    html: str
    status_code: int
    depth: int


@dataclass
class CollectionReport:
    pages_saved: int = 0
    failed_requests: int = 0
    failures: list[dict] = field(default_factory=list)
    candidates: list[str] = field(default_factory=list)
    limit_reached: bool = False


class CollectionEngine(Protocol):
    name: str
    version: str

    async def collect(
        self,
        spec: RunSpec,
        on_page: Callable[[PageEvidence], None],
        *,
        work_dir: Path,
    ) -> CollectionReport: ...
