"""Local run operations shared by interface adapters."""

from __future__ import annotations

import asyncio
from contextlib import AbstractContextManager
from dataclasses import asdict, replace
from datetime import datetime, timezone
import logging
from pathlib import Path
from typing import Protocol

from jevscout.core.engine import CollectionEngine, PageEvidence
from jevscout.modules.jobs.extraction import parse_jobs
from jevscout.core.models import RunRecord


logger = logging.getLogger(__name__)


class RunStore(Protocol):
    def get(self, run_id: str) -> RunRecord: ...
    def update(self, record: RunRecord) -> None: ...
    def operation_lock(self) -> AbstractContextManager[None]: ...
    def engine_workspace(self, run_id: str) -> Path: ...
    def save_page(self, run_id: str, url: str, html: str, metadata: dict) -> str: ...
    def list_pages(self, run_id: str) -> list[dict]: ...
    def read_artifact(self, run_id: str, ref: str) -> str: ...
    def write_execution(self, run_id: str, payload: dict) -> None: ...
    def read_execution(self, run_id: str) -> dict | None: ...
    def save_results(self, run_id: str, items: list[dict]) -> None: ...
    def list_results(self, run_id: str) -> list[dict]: ...
    def save_evaluations(self, run_id: str, evaluations: list[dict]) -> None: ...
    def list_evaluations(self, run_id: str) -> list[dict]: ...


class ApprovalRequired(RuntimeError):
    """Network execution requires user approval through the calling host."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _extract(store: RunStore, run_id: str, india_only: bool = False) -> list[dict]:
    items = []
    for page in store.list_pages(run_id):
        # Only successful HTML pages and feeds are candidates for job extraction.
        status = page["metadata"].get("status_code", 0)
        if not 200 <= status < 300:
            continue
        items.extend(parse_jobs(store.read_artifact(run_id, page["artifact_ref"]),
                                page["url"], page["artifact_ref"],
                                india_only=india_only))
    from jevscout.modules.jobs.filters import classify_job_category
    from jevscout.modules.jobs.company_identity import resolve_company
    for item in items:
        item["company"] = resolve_company(item)
        item["job_category"] = classify_job_category(item)
    store.save_results(run_id, items)
    logger.info("extraction completed run_id=%s items=%d", run_id, len(items))
    return items


def extract_run(store: RunStore, run_id: str, india_only: bool = False) -> list[dict]:
    """Re-extract saved evidence without loading a crawler or making requests."""
    with store.operation_lock():
        return _extract_run_locked(store, run_id, india_only=india_only)


def _extract_run_locked(store: RunStore, run_id: str, india_only: bool = False) -> list[dict]:
    """Extract saved evidence while the caller holds the operation lock."""
    record = store.get(run_id)
    if record.status in {"pending", "running"}:
        raise RuntimeError("run must finish collection before extraction")
    items = _extract(store, run_id, india_only=india_only)
    report = store.read_execution(run_id)
    if report is not None:
        report["items_extracted"] = len(items)
        report["last_extracted_at"] = _now()
        store.write_execution(run_id, report)
    return items


def score_run(
    store: RunStore,
    run_id: str,
    profile: Any,
    client: Any | None = None,
    model: str | None = None,
) -> list[dict]:
    """Score extracted jobs from a run against candidate profile using decision client."""
    from jevscout.modules.jobs.scoring.client import OpenRouterDecisionClient
    from jevscout.modules.jobs.scoring.engine import JobMatchEngine

    with store.operation_lock():
        store.get(run_id)
        results = store.list_results(run_id)
        if not results:
            results = _extract_run_locked(store, run_id)
        if not results:
            return []

        if client is None:
            client = OpenRouterDecisionClient(model=model or "respan/span-01-lite:free")

        engine = JobMatchEngine(client=client)
        evaluations = engine.evaluate_batch(profile, results, model=model)

        serialized = []
        for ev in evaluations:
            dim_answers = {}
            for k, ans in ev.dimension_answers.items():
                if hasattr(ans, "noul"):
                    dim_answers[k] = {"type": "noul", "noul": ans.noul}
                elif hasattr(ans, "choice"):
                    dim_answers[k] = {
                        "type": "choice",
                        "choice": ans.choice,
                        "probabilities": getattr(ans, "probabilities", {}),
                    }
                elif hasattr(ans, "score"):
                    dim_answers[k] = {
                        "type": "score",
                        "score": ans.score,
                        "probabilities": getattr(ans, "probabilities", []),
                    }
            serialized.append({
                "job_id": ev.job_id,
                "job_title": ev.job_title,
                "composite_score": ev.composite_score,
                "recommendation": ev.recommendation.value,
                "model_name": ev.model_name,
                "dimension_answers": dim_answers,
            })

        store.save_evaluations(run_id, serialized)
        logger.info("scoring completed run_id=%s count=%d", run_id, len(serialized))
        return serialized


async def execute_run(
    store: RunStore, run_id: str, *, approved: bool, engine: CollectionEngine | None = None
) -> RunRecord:
    """Execute one pending local run under explicit host-delegated approval.

    A CLI flag is an assertion by the calling host, not authentication of a user.
    No worker queue or restart/resume semantics are implied.
    """
    if not approved:
        raise ApprovalRequired("explicit approval is required before network execution")
    if engine is None:
        from jevscout.adapters.crawling.crawlee import CrawleeEngine
        engine = CrawleeEngine()

    with store.operation_lock():
        record = store.get(run_id)
        if record.status != "pending":
            raise RuntimeError("only pending runs can be executed; create a new run to recollect")
        record = replace(record, status="running", error=None)
        report = {
            "schema_version": 1,
            "engine": engine.name,
            "engine_version": engine.version,
            "approval_mode": "host-delegated",
            "approved_spec": record.spec.to_dict(),
            "started_at": _now(),
            "pages_saved": 0,
            "items_extracted": 0,
            "failed_requests": 0,
            "failures": [],
            "candidates": [],
            "status": "running",
        }
        store.write_execution(run_id, report)
        store.update(record)
        logger.info("collection started run_id=%s", run_id)

        def save_page(page: PageEvidence) -> None:
            store.save_page(run_id, page.url, page.html,
                            {"status_code": page.status_code, "depth": page.depth})
            report["pages_saved"] += 1
            store.write_execution(run_id, report)
            logger.debug("page saved run_id=%s count=%d", run_id, report["pages_saved"])

        try:
            collected = await asyncio.wait_for(
                engine.collect(record.spec, save_page, work_dir=store.engine_workspace(run_id)),
                timeout=record.spec.timeout_seconds,
            )
            report.update(asdict(collected))
            items = _extract(store, run_id)
            report["items_extracted"] = len(items)
            status = "partial" if collected.failed_requests and collected.pages_saved else (
                "failed" if collected.failed_requests else "completed"
            )
            error = "one or more requests failed" if collected.failed_requests else None
        except asyncio.TimeoutError:
            status = "partial" if report["pages_saved"] else "failed"
            error = "collection timed out"
            try:
                report["items_extracted"] = len(_extract(store, run_id))
            except Exception:
                error = "collection timed out; extraction failed"
        except asyncio.CancelledError:
            record = replace(record, status="cancelled", error="collection cancelled")
            report.update(status="cancelled", finished_at=_now(), error=record.error)
            store.update(record)
            store.write_execution(run_id, report)
            logger.info("collection cancelled run_id=%s", run_id)
            raise
        except Exception:
            # Source and library exception messages may contain URLs or secrets.
            status = "partial" if report["pages_saved"] else "failed"
            error = "collection or extraction failed"
        record = replace(record, status=status, error=error)
        report.update(status=status, finished_at=_now(), error=error)
        store.update(record)
        store.write_execution(run_id, report)
        logger.info("collection finished run_id=%s status=%s", run_id, status)
        return record
