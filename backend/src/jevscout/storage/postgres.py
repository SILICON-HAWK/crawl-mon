"""PostgreSQL implementation of the run storage contract."""

import hashlib
import json
import uuid
from contextlib import contextmanager
from pathlib import Path
from threading import RLock
from typing import Any, Iterator

from jevscout.core.models import RunRecord, RunSpec


class PostgresRunStore:
    """Persist run data in PostgreSQL and engine workspaces under ``root``.

    Requires psycopg 3. Call :meth:`initialize_schema` explicitly before use.
    """

    SCHEMA_VERSION = 1

    def __init__(self, dsn: str, root: Path):
        self._dsn = dsn
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._lock_guard = RLock()
        self._lock_connection = None
        self._lock_depth = 0

    def _connect(self):
        try:
            import psycopg
        except ImportError as exc:
            raise RuntimeError("PostgreSQL storage requires psycopg 3") from exc
        try:
            return psycopg.connect(self._dsn)
        except Exception as exc:
            raise RuntimeError("PostgreSQL storage connection failed") from None

    @staticmethod
    def _safe_run_id(run_id: str) -> str:
        try:
            canonical = str(uuid.UUID(run_id))
        except (ValueError, TypeError, AttributeError) as exc:
            raise ValueError("invalid run ID") from exc
        if run_id != canonical:
            raise ValueError("invalid run ID")
        return canonical

    @staticmethod
    def _json(payload: Any) -> str:
        return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)

    @staticmethod
    def _safe_artifact_ref(ref: str) -> str:
        if not isinstance(ref, str) or not ref.startswith("pages/") or not ref.endswith(".html"):
            raise ValueError("invalid artifact reference")
        key = ref[6:-5]
        if len(key) != 64 or any(c not in "0123456789abcdef" for c in key):
            raise ValueError("invalid artifact reference")
        return key

    def initialize_schema(self) -> None:
        """Create the initial schema once; safe to call repeatedly."""
        ddl = """
        CREATE TABLE IF NOT EXISTS jevscout_schema (version INTEGER PRIMARY KEY);
        CREATE TABLE IF NOT EXISTS jevscout_runs (
            id UUID PRIMARY KEY, record JSONB NOT NULL
        );
        CREATE TABLE IF NOT EXISTS jevscout_pages (
            run_id UUID NOT NULL REFERENCES jevscout_runs(id) ON DELETE CASCADE,
            artifact_ref TEXT NOT NULL, page_record JSONB NOT NULL, html TEXT NOT NULL,
            PRIMARY KEY (run_id, artifact_ref)
        );
        CREATE TABLE IF NOT EXISTS jevscout_documents (
            run_id UUID NOT NULL REFERENCES jevscout_runs(id) ON DELETE CASCADE,
            kind TEXT NOT NULL CHECK (kind IN ('execution','results','evaluations')),
            document JSONB NOT NULL, PRIMARY KEY (run_id, kind)
        );
        INSERT INTO jevscout_schema(version) VALUES (1) ON CONFLICT DO NOTHING;
        """
        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(ddl)
                    cur.execute("SELECT version FROM jevscout_schema")
                    versions = [row[0] for row in cur.fetchall()]
                    if versions != [self.SCHEMA_VERSION]:
                        raise RuntimeError("unsupported PostgreSQL storage schema version")
        except RuntimeError:
            raise
        except Exception:
            raise RuntimeError("PostgreSQL schema initialization failed") from None

    def _run(self, run_id: str) -> RunRecord:
        run_id = self._safe_run_id(run_id)
        try:
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute("SELECT record FROM jevscout_runs WHERE id = %s", (run_id,))
                row = cur.fetchone()
        except Exception:
            raise RuntimeError("PostgreSQL storage read failed") from None
        if row is None:
            raise FileNotFoundError(run_id)
        return RunRecord.from_dict(row[0])

    def create(self, spec: RunSpec) -> RunRecord:
        if not isinstance(spec, RunSpec):
            raise TypeError("spec must be a RunSpec")
        record = RunRecord(str(uuid.uuid4()), RunSpec.from_dict(spec.to_dict()))
        try:
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute("INSERT INTO jevscout_runs(id, record) VALUES (%s, %s::jsonb)", (record.id, self._json(record.to_dict())))
        except Exception:
            raise RuntimeError("PostgreSQL run creation failed") from None
        return record

    def get(self, run_id: str) -> RunRecord:
        return self._run(run_id)

    def list_runs(self) -> list[RunRecord]:
        try:
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute("SELECT record FROM jevscout_runs ORDER BY id")
                return [RunRecord.from_dict(row[0]) for row in cur.fetchall()]
        except Exception:
            raise RuntimeError("PostgreSQL run listing failed") from None

    def update(self, record: RunRecord) -> None:
        if not isinstance(record, RunRecord):
            raise TypeError("record must be a RunRecord")
        run_id = self._safe_run_id(record.id)
        try:
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute("UPDATE jevscout_runs SET record = %s::jsonb WHERE id = %s", (self._json(record.to_dict()), run_id))
                if cur.rowcount == 0:
                    raise FileNotFoundError(run_id)
        except FileNotFoundError:
            raise
        except Exception:
            raise RuntimeError("PostgreSQL run update failed") from None

    def save_page(self, run_id: str, url: str, html: str, metadata: dict) -> str:
        if not isinstance(url, str) or not isinstance(html, str) or not isinstance(metadata, dict):
            raise TypeError("url and html must be strings and metadata must be an object")
        RunSpec([url])
        meta = self._json(metadata)
        self._safe_run_id(run_id)
        ref = "pages/" + hashlib.sha256(b"\0".join((url.encode(), html.encode(), meta.encode()))).hexdigest() + ".html"
        try:
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute("SELECT 1 FROM jevscout_runs WHERE id = %s", (run_id,))
                if cur.fetchone() is None:
                    raise FileNotFoundError(run_id)
                record = self._json({"url": url, "artifact_ref": ref, "metadata": metadata})
                cur.execute("INSERT INTO jevscout_pages(run_id, artifact_ref, page_record, html) VALUES (%s,%s,%s::jsonb,%s) ON CONFLICT DO NOTHING", (run_id, ref, record, html))
        except FileNotFoundError:
            raise
        except Exception:
            raise RuntimeError("PostgreSQL page save failed") from None
        return ref

    def list_pages(self, run_id: str) -> list[dict[str, Any]]:
        self._run(run_id)
        try:
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute("SELECT page_record FROM jevscout_pages WHERE run_id = %s ORDER BY artifact_ref", (run_id,))
                return [row[0] for row in cur.fetchall()]
        except Exception:
            raise RuntimeError("PostgreSQL page listing failed") from None

    def read_artifact(self, run_id: str, ref: str) -> str:
        self._safe_artifact_ref(ref)
        run_id = self._safe_run_id(run_id)
        try:
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute("SELECT html FROM jevscout_pages WHERE run_id = %s AND artifact_ref = %s", (run_id, ref))
                row = cur.fetchone()
        except Exception:
            raise RuntimeError("PostgreSQL artifact read failed") from None
        if row is None:
            raise FileNotFoundError(ref)
        return row[0]

    def engine_workspace(self, run_id: str) -> Path:
        self._run(run_id)
        path = self.root / "runs" / self._safe_run_id(run_id) / "engine"
        path.mkdir(parents=True, exist_ok=True, mode=0o700)
        return path.resolve()

    @staticmethod
    def _object(payload: object, name: str) -> dict:
        if not isinstance(payload, dict):
            raise TypeError(f"{name} must be an object")
        PostgresRunStore._json(payload)
        return payload

    def _write_document(self, run_id: str, kind: str, value: Any) -> None:
        encoded = self._json(value)
        self._run(run_id)
        try:
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute("INSERT INTO jevscout_documents(run_id,kind,document) VALUES (%s,%s,%s::jsonb) ON CONFLICT (run_id,kind) DO UPDATE SET document=EXCLUDED.document", (run_id, kind, encoded))
        except Exception:
            raise RuntimeError("PostgreSQL document write failed") from None

    def _read_document(self, run_id: str, kind: str, default: Any) -> Any:
        self._run(run_id)
        try:
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute("SELECT document FROM jevscout_documents WHERE run_id=%s AND kind=%s", (run_id, kind))
                row = cur.fetchone()
                return default if row is None else row[0]
        except Exception:
            raise RuntimeError("PostgreSQL document read failed") from None

    def write_execution(self, run_id: str, payload: dict) -> None:
        self._write_document(run_id, "execution", self._object(payload, "execution payload"))

    def read_execution(self, run_id: str) -> dict | None:
        value = self._read_document(run_id, "execution", None)
        return None if value is None else self._object(value, "stored execution payload")

    def save_results(self, run_id: str, items: list[dict]) -> None:
        if not isinstance(items, list) or any(not isinstance(item, dict) for item in items):
            raise TypeError("results must be a list of objects")
        self._write_document(run_id, "results", {"schema_version": 1, "parser_version": "jsonld-jobs-v1", "items": items})

    def list_results(self, run_id: str) -> list[dict]:
        doc = self._read_document(run_id, "results", None)
        if doc is None:
            return []
        if not isinstance(doc, dict) or doc.get("schema_version") != 1 or doc.get("parser_version") != "jsonld-jobs-v1" or not isinstance(doc.get("items"), list) or any(not isinstance(x, dict) for x in doc["items"]):
            raise ValueError("stored results have an invalid format")
        return doc["items"]

    def save_evaluations(self, run_id: str, evaluations: list[dict]) -> None:
        if not isinstance(evaluations, list) or any(not isinstance(item, dict) for item in evaluations):
            raise TypeError("evaluations must be a list of objects")
        self._write_document(run_id, "evaluations", {"schema_version": 1, "evaluations": evaluations})

    def list_evaluations(self, run_id: str) -> list[dict]:
        doc = self._read_document(run_id, "evaluations", None)
        if doc is None:
            return []
        if not isinstance(doc, dict) or doc.get("schema_version") != 1 or not isinstance(doc.get("evaluations"), list) or any(not isinstance(x, dict) for x in doc["evaluations"]):
            raise ValueError("stored evaluations have an invalid format")
        return doc["evaluations"]

    @contextmanager
    def operation_lock(self) -> Iterator[None]:
        with self._lock_guard:
            if self._lock_depth:
                self._lock_depth += 1
                try:
                    yield
                finally:
                    self._lock_depth -= 1
                return
            conn = self._connect()
            conn.autocommit = True
            try:
                # PostgreSQL advisory locks are scoped to the connected database.
                # A fixed namespaced key therefore coordinates containers even
                # when their engine workspace roots differ.
                lock_key = "jevscout:postgres-run-store:operation:v1"
                try:
                    with conn.cursor() as cur:
                        cur.execute("SELECT pg_try_advisory_lock(hashtextextended(%s, 0))", (lock_key,))
                        acquired = cur.fetchone()[0]
                except Exception:
                    raise RuntimeError("PostgreSQL operation lock failed") from None
                if not acquired:
                    raise RuntimeError("another operation is active")
                self._lock_connection = conn
                self._lock_depth = 1
                try:
                    yield
                finally:
                    self._lock_depth = 0
                    self._lock_connection = None
                    try:
                        with conn.cursor() as cur:
                            cur.execute("SELECT pg_advisory_unlock(hashtextextended(%s, 0))", (lock_key,))
                    except Exception:
                        raise RuntimeError("PostgreSQL operation lock release failed") from None
            finally:
                conn.close()
