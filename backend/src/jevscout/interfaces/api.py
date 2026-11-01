"""Local HTTP adapter for inspecting saved runs and starting pipelines.

Run with ``uvicorn jevscout.interfaces.api:app --host 127.0.0.1 --port 8000``.
The server intentionally binds to loopback; pipeline collection starts only after
an explicit POST to ``/api/pipeline``.
"""

from __future__ import annotations

import os
import json
import fcntl
import hashlib
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlsplit, urlunsplit

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from jevscout.storage.filesystem import FileRunStore
from jevscout.application.profile import ProfileStore
from jevscout.application.job_actions import JobActionsStore
from jevscout.application.availability import AvailabilityStore, AvailabilityManager


class CandidateProfileInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role_target: str = Field(min_length=1, max_length=200)
    primary_skills: list[str] = Field(default_factory=list, max_length=50)
    experience_years: float = Field(default=3.0, ge=0, le=80)
    preferred_locations: list[str] = Field(default_factory=lambda: ["India"], max_length=20)
    remote_only: bool = False
    secondary_skills: list[str] = Field(default_factory=list, max_length=50)
    min_salary_inr: float | None = Field(default=None, ge=0)


class PipelineRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    seed_urls: list[str] = Field(min_length=1, max_length=5)
    profile: CandidateProfileInput


class StructuredProfileInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role_target: str = Field(default="Software Engineer", min_length=1, max_length=200)
    primary_skills: list[str] = Field(default_factory=list, max_length=50)
    experience_years: float = Field(default=3.0, ge=0, le=80)
    preferred_locations: list[str] = Field(default_factory=lambda: ["India"], max_length=20)
    remote_only: bool = False
    secondary_skills: list[str] = Field(default_factory=list, max_length=50)
    min_salary_inr: float | None = Field(default=None, ge=0)


class ClassificationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str
    run_id: str
    job_index: int = Field(ge=0, le=100000)


class AvailabilityRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    urls: list[str] = Field(min_length=1, max_length=100)
    approved: Literal[True]


class ProfileInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    freeform_context: str = Field(default="", max_length=20000)
    structured_fields: StructuredProfileInput = Field(default_factory=StructuredProfileInput)


class JobActionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_url: str = Field(min_length=1, max_length=8192)
    status: Literal["interested", "not_interested", "unset"]


def _canonical_application_url(value: object) -> str | None:
    """Normalize only URL components that do not change the application target."""
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = urlsplit(value)
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
            return None
        if parsed.username is not None or parsed.password is not None:
            return None
        port = parsed.port
        host = parsed.hostname.lower()
        if ":" in host:
            host = f"[{host}]"
        if port is not None and not (parsed.scheme.lower() == "https" and port == 443) and not (
            parsed.scheme.lower() == "http" and port == 80
        ):
            host = f"{host}:{port}"
        path = parsed.path.rstrip("/") or "/"
        return urlunsplit((parsed.scheme.lower(), host, path, parsed.query, ""))
    except ValueError:
        return None


@contextmanager
def _decision_lock(root: Path, username: str, run_id: str, job_index: int):
    """Serialize requests for the same saved decision across local API processes."""
    directory = Path(root) / ".decision-locks"
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    name = hashlib.sha256(f"{username}:{run_id}:{job_index}".encode()).hexdigest()
    with (directory / name).open("a+b") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def create_app(*, store: Any | None = None, pipeline_manager: Any | None = None) -> FastAPI:
    """Build an API app, allowing tests and embedding hosts to inject stores."""
    app = FastAPI(title="JevScout local API", version="0.1.0")
    run_store = store or FileRunStore(
        Path(os.environ.get("JEVSCOUT_DATA_DIR", "data/live-trial"))
    )
    app.state.run_store = run_store
    profile_root = Path(os.environ.get("JEVSCOUT_USER_ASSETS_DIR", str((run_store.root / "user-assets") if store is not None else Path("user-assets"))))
    profile_store = ProfileStore(profile_root)
    app.state.profile_store = profile_store
    job_actions_store = JobActionsStore(profile_root)
    app.state.job_actions_store = job_actions_store
    availability_store = AvailabilityStore(run_store.root / "listing-availability.json")
    availability_manager = AvailabilityManager(availability_store)
    app.state.availability_manager = availability_manager

    if pipeline_manager is None:
        from jevscout.application.pipeline import PipelineManager

        pipeline_manager = PipelineManager(run_store)
    app.state.pipeline_manager = pipeline_manager

    @app.get("/api/runs")
    def list_runs() -> list[dict[str, Any]]:
        return [record.to_dict() for record in run_store.list_runs()]

    @app.get("/api/jobs")
    def list_jobs(technical_only: bool = True) -> list[dict[str, Any]]:
        """Aggregate saved extracted jobs, newest run first, retaining source indices."""
        from jevscout.modules.jobs.filters import classify_job_category
        from jevscout.modules.jobs.company_identity import resolve_company
        records = sorted(run_store.list_runs(), key=lambda record: record.created_at, reverse=True)
        jobs: list[dict[str, Any]] = []
        by_url: dict[str, dict[str, Any]] = {}
        for record in records:
            for job_index, source_job in enumerate(run_store.list_results(record.id)):
                category = classify_job_category(source_job)
                if technical_only and category != "technical":
                    continue
                provenance = {"run_id": record.id, "job_index": job_index}
                job = {**source_job, "company": resolve_company(source_job), "job_category": category, **provenance, "originals": [provenance]}
                key = _canonical_application_url(source_job.get("application_url"))
                existing = by_url.get(key) if key else None
                if existing is not None:
                    existing["originals"].append(provenance)
                    continue
                jobs.append(job)
                if key:
                    by_url[key] = job
        checks = availability_store.read()
        for job in jobs:
            record = checks.get(job.get("application_url"))
            job["availability"] = record.to_dict() if record else None
        priority = {"available": 0, "unknown": 2, "unavailable": 3}
        jobs.sort(key=lambda job: priority.get((job.get("availability") or {}).get("state"), 1))
        return jobs

    @app.get("/api/company-sources")
    def company_sources() -> list[dict[str, Any]]:
        """Suggest recognized employer-hosted feeds from saved job links."""
        from jevscout.modules.jobs.company_discovery import career_feed_candidate
        candidates: dict[str, dict[str, Any]] = {}
        for job in list_jobs():
            for link in (job.get("application_url"), job.get("listing_url")):
                feed = career_feed_candidate(link)
                if feed and feed not in candidates:
                    candidates[feed] = {"company": job.get("company"), "feed_url": feed,
                                        "discovered_from": link, "status": "unverified"}
        return list(candidates.values())

    @app.get("/api/availability")
    def availability_status() -> dict[str, Any]:
        return availability_manager.status()

    @app.post("/api/availability/check", status_code=202)
    def check_availability(request: AvailabilityRequest) -> dict[str, Any]:
        try:
            return availability_manager.start(request.urls)
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid listing URLs") from None
        except RuntimeError:
            raise HTTPException(status_code=409, detail="An availability check is already running") from None

    @app.get("/api/profile/{username}")
    def get_profile(username: str) -> dict[str, Any]:
        try:
            return profile_store.get(username)
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid profile") from None
        except (TypeError, OSError):
            raise HTTPException(status_code=422, detail="Invalid profile") from None
        except (OSError, json.JSONDecodeError):
            raise HTTPException(status_code=500, detail="Could not read profile") from None

    @app.put("/api/profile/{username}")
    def put_profile(username: str, request: ProfileInput) -> dict[str, Any]:
        try:
            return profile_store.put(
                username,
                freeform_context=request.freeform_context,
                structured_fields=request.structured_fields.model_dump(),
            )
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid profile") from None

    @app.get("/api/profile/{username}/job-actions")
    def get_job_actions(username: str) -> dict[str, str]:
        try:
            return job_actions_store.get(username)
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid job actions request") from None
        except (OSError, json.JSONDecodeError):
            raise HTTPException(status_code=500, detail="Could not read job actions") from None

    @app.put("/api/profile/{username}/job-actions")
    def put_job_action(username: str, request: JobActionInput) -> dict[str, str]:
        try:
            return job_actions_store.set(username, request.job_url, request.status)
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid job actions request") from None
        except (OSError, TypeError):
            raise HTTPException(status_code=500, detail="Could not save job action") from None

    @app.get("/api/runs/{run_id}/results")
    def get_results(run_id: str) -> list[dict[str, Any]]:
        try:
            return run_store.list_results(run_id)
        except (ValueError, FileNotFoundError):
            raise HTTPException(status_code=404, detail="Run not found") from None

    @app.post("/api/classify")
    def classify(request: ClassificationRequest) -> dict[str, Any]:
        # The user explicitly requests sending their profile and this job to OpenRouter.
        from jevscout.application.classification import classify_job
        from jevscout.modules.jobs.scoring.client import OpenRouterDecisionClient
        try:
            if not profile_store.exists(request.username):
                raise HTTPException(status_code=404, detail="Profile not found; save it on the Profile page")
            profile = profile_store.get(request.username)
            if not profile.get("freeform_context", "").strip():
                raise HTTPException(status_code=400, detail="Save candidate context before classification")
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid profile name") from None
        try:
            jobs = run_store.list_results(request.run_id)
            job = jobs[request.job_index]
        except (IndexError, ValueError, FileNotFoundError):
            raise HTTPException(status_code=404, detail="Job not found; refresh the Jobs page") from None
        with _decision_lock(run_store.root, request.username, request.run_id, request.job_index):
            try:
                previous = run_store.list_evaluations(request.run_id)
            except (OSError, ValueError):
                raise HTTPException(status_code=503, detail="Could not read saved decisions") from None
            for item in reversed(previous):
                if (item.get("job_index") == request.job_index and item.get("username") == request.username
                        and isinstance(item.get("dimensions"), dict) and item["dimensions"]):
                    return {**item, "cached": True}
            job_url = _canonical_application_url(job.get("application_url"))
            if job_url:
                for other in run_store.list_runs():
                    if other.id == request.run_id:
                        continue
                    try:
                        other_jobs = run_store.list_results(other.id)
                        other_evaluations = run_store.list_evaluations(other.id)
                    except (OSError, ValueError):
                        continue
                    matches = {index for index, candidate in enumerate(other_jobs)
                               if _canonical_application_url(candidate.get("application_url")) == job_url}
                    for item in reversed(other_evaluations):
                        if (item.get("job_index") in matches and item.get("username") == request.username
                                and isinstance(item.get("dimensions"), dict) and item["dimensions"]):
                            return {**item, "cached": True, "source_run_id": other.id}
            key = os.environ.get("OPENROUTER_API_KEY", "")
            if not key:
                env_file = Path(".env")
                if env_file.is_file():
                    for line in env_file.read_text(encoding="utf-8").splitlines():
                        if line.strip().startswith("OPENROUTER_API_KEY="):
                            key = line.split("=", 1)[1].strip().strip("\"'")
                            break
            if not key:
                raise HTTPException(status_code=400, detail="OpenRouter key is not configured")
            try:
                result = classify_job(job, profile, OpenRouterDecisionClient(api_key=key, model="respan/span-01-lite:free"))
            except Exception as exc:
                if "HTTP 429" in str(exc):
                    raise HTTPException(status_code=429, detail="OpenRouter rate limit reached; try later. Saved decisions are still available.") from None
                raise HTTPException(status_code=502, detail="Decision model request failed; try again later") from None
            result.update(run_id=request.run_id, job_index=request.job_index)
            try:
                with run_store.operation_lock():
                    previous = run_store.list_evaluations(request.run_id)
                    previous = [item for item in previous if not (item.get("job_index") == request.job_index and item.get("username") == request.username)]
                    previous.append({**result, "username": request.username})
                    run_store.save_evaluations(request.run_id, previous)
            except Exception:
                raise HTTPException(status_code=503, detail="Analysis completed but could not be saved; storage may be busy") from None
            return {**result, "cached": False}

    @app.get("/api/runs/{run_id}/evaluations")
    def list_evaluations(run_id: str) -> list[dict[str, Any]]:
        try:
            return run_store.list_evaluations(run_id)
        except (ValueError, FileNotFoundError):
            raise HTTPException(status_code=404, detail="Run not found") from None

    @app.get("/api/pipeline")
    def list_pipeline() -> list[dict[str, Any]]:
        return pipeline_manager.list()

    @app.post("/api/pipeline", status_code=202)
    def start_pipeline(request: PipelineRequest) -> dict[str, Any]:
        # This explicit request is the caller's approval to perform collection.
        try:
            return pipeline_manager.start(
                seed_urls=request.seed_urls,
                profile=request.profile.model_dump(),
            )
        except (ValueError, TypeError):
            raise HTTPException(status_code=422, detail="Invalid pipeline request") from None
        except RuntimeError:
            raise HTTPException(status_code=409, detail="Pipeline capacity is unavailable") from None

    @app.get("/api/pipeline/{pipeline_id}")
    def get_pipeline(pipeline_id: str) -> dict[str, Any]:
        try:
            return pipeline_manager.get(pipeline_id)
        except (ValueError, KeyError, FileNotFoundError):
            raise HTTPException(status_code=404, detail="Pipeline not found") from None

    return app


app = create_app()
