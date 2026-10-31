"""Local HTTP adapter for inspecting saved runs and starting pipelines.

Run with ``uvicorn jevscout.interfaces.api:app --host 127.0.0.1 --port 8000``.
The server intentionally binds to loopback; pipeline collection starts only after
an explicit POST to ``/api/pipeline``.
"""

from __future__ import annotations

import os
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from jevscout.storage.filesystem import FileRunStore
from jevscout.application.profile import ProfileStore


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


class ProfileInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    freeform_context: str = Field(default="", max_length=20000)
    structured_fields: StructuredProfileInput = Field(default_factory=StructuredProfileInput)


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


def create_app(*, store: Any | None = None, pipeline_manager: Any | None = None) -> FastAPI:
    """Build an API app, allowing tests and embedding hosts to inject stores."""
    app = FastAPI(title="JevScout local API", version="0.1.0")
    run_store = store or FileRunStore(
        Path(os.environ.get("JEVSCOUT_DATA_DIR", "data"))
    )
    app.state.run_store = run_store
    profile_root = Path(os.environ.get("JEVSCOUT_USER_ASSETS_DIR", str((run_store.root / "user-assets") if store is not None else Path("user-assets"))))
    profile_store = ProfileStore(profile_root)
    app.state.profile_store = profile_store

    if pipeline_manager is None:
        from jevscout.application.pipeline import PipelineManager

        pipeline_manager = PipelineManager(run_store)
    app.state.pipeline_manager = pipeline_manager

    @app.get("/api/runs")
    def list_runs() -> list[dict[str, Any]]:
        return [record.to_dict() for record in run_store.list_runs()]

    @app.get("/api/jobs")
    def list_jobs() -> list[dict[str, Any]]:
        """Aggregate saved extracted jobs, newest run first, retaining source indices."""
        records = sorted(run_store.list_runs(), key=lambda record: record.created_at, reverse=True)
        jobs: list[dict[str, Any]] = []
        by_url: dict[str, dict[str, Any]] = {}
        for record in records:
            for job_index, source_job in enumerate(run_store.list_results(record.id)):
                provenance = {"run_id": record.id, "job_index": job_index}
                job = {**source_job, **provenance, "originals": [provenance]}
                key = _canonical_application_url(source_job.get("application_url"))
                existing = by_url.get(key) if key else None
                if existing is not None:
                    existing["originals"].append(provenance)
                    continue
                jobs.append(job)
                if key:
                    by_url[key] = job
        return jobs

    @app.get("/api/profile/{username}")
    def get_profile(username: str) -> dict[str, Any]:
        try:
            return profile_store.get(username)
        except ValueError:
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
        except (TypeError, OSError):
            raise HTTPException(status_code=422, detail="Invalid profile") from None

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
            result.update(run_id=request.run_id, job_index=request.job_index)
            with run_store.operation_lock():
                previous = run_store.list_evaluations(request.run_id)
                previous = [item for item in previous if not (item.get("job_index") == request.job_index and item.get("username") == request.username)]
                previous.append({**result, "username": request.username})
                run_store.save_evaluations(request.run_id, previous)
            return result
        except Exception:
            raise HTTPException(status_code=502, detail="Decision model request or result storage failed") from None

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
