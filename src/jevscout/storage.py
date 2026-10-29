"""Single-process filesystem persistence for run metadata and saved pages."""

import hashlib
import json
import os
import tempfile
import uuid
from pathlib import Path
from typing import Any

from .models import RunRecord, RunSpec


class FileRunStore:
    """Persist runs and page artifacts for one synchronous application process.

    This store is single-writer. It does not provide a queue, crash recovery,
    or multi-writer coordination.
    """

    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.runs_dir = self.root / "runs"
        self.runs_dir.mkdir(mode=0o700, exist_ok=True)

    @staticmethod
    def _safe_run_id(run_id: str) -> str:
        try:
            parsed = uuid.UUID(run_id)
        except (ValueError, TypeError, AttributeError) as exc:
            raise ValueError("invalid run ID") from exc
        canonical = str(parsed)
        if run_id != canonical:
            raise ValueError("invalid run ID")
        return canonical

    def _run_dir(self, run_id: str) -> Path:
        return self.runs_dir / self._safe_run_id(run_id)

    @staticmethod
    def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        temporary_name = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=path.parent, prefix=".tmp-", delete=False
            ) as temporary:
                temporary_name = temporary.name
                json.dump(payload, temporary, ensure_ascii=False, sort_keys=True)
                temporary.write("\n")
                temporary.flush()
                os.fsync(temporary.fileno())
            os.replace(temporary_name, path)
        finally:
            if temporary_name is not None and os.path.exists(temporary_name):
                os.unlink(temporary_name)

    @staticmethod
    def _atomic_text(path: Path, value: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        temporary_name = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=path.parent, prefix=".tmp-", delete=False
            ) as temporary:
                temporary_name = temporary.name
                temporary.write(value)
                temporary.flush()
                os.fsync(temporary.fileno())
            os.replace(temporary_name, path)
        finally:
            if temporary_name is not None and os.path.exists(temporary_name):
                os.unlink(temporary_name)

    def create(self, spec: RunSpec) -> RunRecord:
        if not isinstance(spec, RunSpec):
            raise TypeError("spec must be a RunSpec")
        snapshot = RunSpec.from_dict(spec.to_dict())
        record = RunRecord(id=str(uuid.uuid4()), spec=snapshot)
        run_dir = self._run_dir(record.id)
        run_dir.mkdir(mode=0o700)
        (run_dir / "pages").mkdir(mode=0o700)
        self._atomic_json(run_dir / "run.json", record.to_dict())
        return record

    def get(self, run_id: str) -> RunRecord:
        path = self._run_dir(run_id) / "run.json"
        with path.open("r", encoding="utf-8") as source:
            return RunRecord.from_dict(json.load(source))

    def list_runs(self) -> list[RunRecord]:
        records = []
        for run_dir in sorted(self.runs_dir.iterdir(), key=lambda item: item.name):
            if run_dir.is_dir() and (run_dir / "run.json").is_file():
                records.append(self.get(run_dir.name))
        return records

    def update(self, record: RunRecord) -> None:
        if not isinstance(record, RunRecord):
            raise TypeError("record must be a RunRecord")
        run_dir = self._run_dir(record.id)
        path = run_dir / "run.json"
        if not path.is_file():
            raise FileNotFoundError(path)
        self._atomic_json(path, record.to_dict())

    def save_page(self, run_id: str, url: str, html: str, metadata: dict) -> str:
        if not isinstance(url, str) or not isinstance(html, str) or not isinstance(metadata, dict):
            raise TypeError("url and html must be strings and metadata must be an object")
        RunSpec([url])
        canonical_metadata = json.dumps(
            metadata, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
        )
        pages_dir = self._run_dir(run_id) / "pages"
        if not pages_dir.is_dir():
            raise FileNotFoundError(pages_dir)
        page_identity = b"\0".join(
            (url.encode("utf-8"), html.encode("utf-8"), canonical_metadata.encode("utf-8"))
        )
        page_key = hashlib.sha256(page_identity).hexdigest()
        artifact_ref = f"pages/{page_key}.html"
        artifact_path = pages_dir / f"{page_key}.html"
        metadata_path = pages_dir / f"{page_key}.json"
        self._atomic_text(artifact_path, html)
        self._atomic_json(metadata_path, {"url": url, "artifact_ref": artifact_ref, "metadata": metadata})
        return artifact_ref

    def list_pages(self, run_id: str) -> list[dict[str, Any]]:
        pages_dir = self._run_dir(run_id) / "pages"
        if not pages_dir.is_dir():
            raise FileNotFoundError(pages_dir)
        pages = []
        for metadata_path in sorted(pages_dir.glob("*.json"), key=lambda item: item.name):
            with metadata_path.open("r", encoding="utf-8") as source:
                pages.append(json.load(source))
        return pages

    @staticmethod
    def _safe_artifact_ref(artifact_ref: str) -> str:
        if not isinstance(artifact_ref, str) or not artifact_ref.startswith("pages/") or not artifact_ref.endswith(".html"):
            raise ValueError("invalid artifact reference")
        page_key = artifact_ref[len("pages/") : -len(".html")]
        if len(page_key) != 64 or any(char not in "0123456789abcdef" for char in page_key):
            raise ValueError("invalid artifact reference")
        return page_key

    def read_artifact(self, run_id: str, ref: str) -> str:
        page_key = self._safe_artifact_ref(ref)
        path = self._run_dir(run_id) / "pages" / f"{page_key}.html"
        return path.read_text(encoding="utf-8")
