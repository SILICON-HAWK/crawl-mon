"""Local HTTP adapter for inspecting saved runs and starting pipelines.

Run with ``uvicorn jevscout.interfaces.api:app --host 127.0.0.1 --port 8000``.
The server intentionally binds to loopback; pipeline collection starts only after
an explicit POST to ``/api/pipeline``.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from jevscout.storage.filesystem import FileRunStore


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


def create_app(*, store: Any | None = None, pipeline_manager: Any | None = None) -> FastAPI:
    """Build an API app, allowing tests and embedding hosts to inject stores."""
    app = FastAPI(title="JevScout local API", version="0.1.0")
    run_store = store or FileRunStore(
        Path(os.environ.get("JEVSCOUT_DATA_DIR", "data"))
    )
    app.state.run_store = run_store

    if pipeline_manager is None:
        from jevscout.application.pipeline import PipelineManager

        pipeline_manager = PipelineManager(run_store)
    app.state.pipeline_manager = pipeline_manager

    @app.get("/api/runs")
    def list_runs() -> list[dict[str, Any]]:
        return [record.to_dict() for record in run_store.list_runs()]

    @app.get("/api/runs/{run_id}/results")
    def get_results(run_id: str) -> list[dict[str, Any]]:
        try:
            return run_store.list_results(run_id)
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
