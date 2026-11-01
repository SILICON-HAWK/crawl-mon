"""Bounded, explicitly started source collection and offline job ranking."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import math
import threading
import uuid
from typing import Any

from jevscout.application.operations import execute_run
from jevscout.core.models import RunSpec
from jevscout.modules.jobs.scoring.models import CandidateProfile
from jevscout.modules.jobs.filters import is_technical_job


MAX_SEEDS = 5
MAX_PAGES_PER_SEED = 5
MAX_TIMEOUT_SECONDS = 120


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _profile(value: CandidateProfile | dict[str, Any]) -> CandidateProfile:
    if isinstance(value, CandidateProfile):
        profile = value
    elif isinstance(value, dict):
        allowed = {"role_target", "primary_skills", "experience_years", "preferred_locations",
                   "remote_only", "secondary_skills", "min_salary_inr"}
        unknown = value.keys() - allowed
        if unknown:
            raise ValueError(f"unknown profile fields: {', '.join(sorted(unknown))}")
        try:
            profile = CandidateProfile(**value)
        except TypeError as exc:
            raise ValueError("profile is missing required fields") from exc
    else:
        raise TypeError("profile must be a CandidateProfile or object")
    if (not isinstance(profile.role_target, str) or not profile.role_target.strip()
            or not isinstance(profile.primary_skills, list)
            or not all(isinstance(x, str) for x in profile.primary_skills)
            or not isinstance(profile.secondary_skills, list)
            or not all(isinstance(x, str) for x in profile.secondary_skills)
            or not isinstance(profile.preferred_locations, list)
            or not all(isinstance(x, str) for x in profile.preferred_locations)
            or isinstance(profile.experience_years, bool)
            or not isinstance(profile.experience_years, (int, float))
            or not isinstance(profile.remote_only, bool)
            or not math.isfinite(profile.experience_years)
            or profile.experience_years < 0
            or any(not item.strip() for item in profile.primary_skills)
            or any(not item.strip() for item in profile.secondary_skills)
            or any(not item.strip() for item in profile.preferred_locations)):
        raise ValueError("profile fields have invalid values")
    return profile


def _rank(job: dict, profile: CandidateProfile) -> tuple[float, list[str]]:
    text = " ".join(str(job.get(key) or "") for key in ("title", "description")).casefold()
    skills = list(dict.fromkeys(profile.primary_skills + profile.secondary_skills))
    matched = [skill for skill in skills if skill.casefold() in text]
    score = 55.0 * len(matched) / max(1, len(skills))
    title = str(job.get("title") or "").casefold()
    target_words = [word for word in profile.role_target.casefold().split() if len(word) > 2]
    if target_words:
        score += 25.0 * sum(word in title for word in target_words) / len(target_words)
    location = str(job.get("location") or "").casefold()
    if any(loc.strip() and loc.casefold() in location for loc in profile.preferred_locations):
        score += 15.0
    elif profile.remote_only and "remote" in location:
        score += 15.0
    return round(min(100.0, score), 1), matched


class PipelineManager:
    """Single-process manager with at most one bounded pipeline worker."""

    def __init__(self, store, engine=None):
        self.store = store
        self.engine = engine
        self._lock = threading.RLock()
        self._states: dict[str, dict] = {}
        self._active = False

    def list(self) -> list[dict]:
        with self._lock:
            return [self._copy(s) for s in self._states.values()]

    def get(self, pipeline_id: str) -> dict:
        try:
            pipeline_id = str(uuid.UUID(pipeline_id))
        except (ValueError, TypeError, AttributeError) as exc:
            raise ValueError("invalid pipeline ID") from exc
        with self._lock:
            if pipeline_id not in self._states:
                raise KeyError(pipeline_id)
            return self._copy(self._states[pipeline_id])

    @staticmethod
    def _copy(state: dict) -> dict:
        # Return detached JSON-shaped state so callers cannot mutate worker state.
        import copy
        return copy.deepcopy(state)

    def start(self, seed_urls: list[str], profile: CandidateProfile | dict[str, Any]) -> dict:
        if not isinstance(seed_urls, list) or not 1 <= len(seed_urls) <= MAX_SEEDS:
            raise ValueError(f"seed_urls must contain between 1 and {MAX_SEEDS} URLs")
        if not all(isinstance(url, str) for url in seed_urls):
            raise ValueError("seed_urls must contain strings")
        if len(set(seed_urls)) != len(seed_urls):
            raise ValueError("seed_urls must be unique")
        # Validates each URL before creating state or starting network activity.
        RunSpec(seed_urls, max_pages=MAX_PAGES_PER_SEED, max_depth=0,
                timeout_seconds=MAX_TIMEOUT_SECONDS, allow_local=False)
        candidate = _profile(profile)
        with self._lock:
            if self._active:
                raise RuntimeError("a pipeline is already running")
            pipeline_id = str(uuid.uuid4())
            state = {
                "id": pipeline_id, "status": "queued", "created_at": _now(),
                "finished_at": None, "seed_urls": list(seed_urls),
                "total_sources": len(seed_urls), "completed_sources": 0,
                "current_source": None, "runs": [], "results": [], "error": None,
            }
            self._states[pipeline_id] = state
            self._active = True
            worker = threading.Thread(target=self._work,
                                      args=(pipeline_id, candidate), daemon=True,
                                      name=f"jevscout-pipeline-{pipeline_id[:8]}")
            worker.start()
            return self._copy(state)

    def _work(self, pipeline_id: str, profile: CandidateProfile) -> None:
        with self._lock:
            state = self._states[pipeline_id]
            state["status"] = "running"
        any_failure = False
        try:
            for seed in state["seed_urls"]:
                with self._lock:
                    state["current_source"] = seed
                run = self.store.create(RunSpec(
                    [seed], max_pages=MAX_PAGES_PER_SEED, max_depth=0,
                    timeout_seconds=MAX_TIMEOUT_SECONDS, allow_local=False,
                ))
                ranked = []
                try:
                    finished = asyncio.run(execute_run(
                        self.store, run.id, approved=True, engine=self.engine,
                    ))
                    jobs = self.store.list_results(run.id)
                    item = {"run_id": run.id, "seed_url": seed, "status": finished.status,
                            "pages_saved": (self.store.read_execution(run.id) or {}).get("pages_saved", 0),
                            "items_found": len(jobs)}
                    if finished.status != "completed":
                        any_failure = True
                    for job_index, job in enumerate(jobs):
                        if not is_technical_job(job):
                            continue
                        score, matched = _rank(job, profile)
                        ranked.append({
                            "run_id": run.id, "job_id": f"{run.id}:{job_index}",
                            "title": job.get("title"), "company": job.get("company"),
                            "location": job.get("location"),
                            "url": job.get("application_url") or job.get("url"),
                            "listing_url": job.get("listing_url"),
                            "source_name": job.get("source_name"),
                            "source_link": job.get("source_link"),
                            "score": score, "matched_skills": matched,
                            "provenance": {"seed_url": seed, "run_id": run.id,
                                           "source_platform": job.get("source_platform")},
                        })
                except Exception:
                    any_failure = True
                    item = {"run_id": run.id, "seed_url": seed, "status": "failed",
                            "pages_saved": 0, "items_found": 0}
                with self._lock:
                    state["runs"].append(item)
                    state["results"].extend(ranked)
                    state["completed_sources"] += 1
                    state["results"].sort(key=lambda result: (-result["score"], result["title"] or ""))
            with self._lock:
                state["status"] = ("failed" if all(item["status"] == "failed" for item in state["runs"]) else "partial") if any_failure else "completed"
        except Exception:
            # Do not expose source/library exception messages which may contain credentials.
            with self._lock:
                state["status"] = "failed"
                state["error"] = "pipeline processing failed"
        finally:
            with self._lock:
                state["current_source"] = None
                state["finished_at"] = _now()
                self._active = False
