from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Protocol, Union

from jevscout.modules.jobs.scoring.models import (
    ChoiceAnswer,
    DecisionAnswer,
    NoulAnswer,
    ScoreAnswer,
)

OPENROUTER_DECISIONS_URL = "https://openrouter.ai/api/alpha/decisions"


class DecisionClient(Protocol):
    def evaluate(
        self,
        state: Union[str, Dict[str, Any], List[Any]],
        questions: Dict[str, Dict[str, Any]],
        *,
        model: Optional[str] = None,
    ) -> Dict[str, DecisionAnswer]:
        ...


class LocalHeuristicDecisionClient:
    """Offline heuristic decision client for local development and testing without network."""

    def __init__(self, model: str = "local/heuristic-v1") -> None:
        self.model = model

    def evaluate(
        self,
        state: Union[str, Dict[str, Any], List[Any]],
        questions: Dict[str, Dict[str, Any]],
        *,
        model: Optional[str] = None,
    ) -> Dict[str, DecisionAnswer]:
        if not isinstance(state, dict):
            # Fallback for raw string or array state
            return {
                q_name: NoulAnswer(type="noul", noul=0.5)
                for q_name in questions
            }

        candidate = state.get("candidate", {})
        job = state.get("job", {})

        job_title = (job.get("title") or "").lower()
        job_loc = (job.get("location") or "").lower()
        job_desc = (job.get("description_summary") or "").lower()

        pref_locs = [str(l).lower() for l in candidate.get("preferred_locations", [])]
        remote_only = candidate.get("remote_only", False)
        target_role = (candidate.get("role_target") or "").lower()
        primary_skills = [str(s).lower() for s in candidate.get("primary_skills", [])]
        cand_years = float(candidate.get("experience_years", 0.0))

        answers: Dict[str, DecisionAnswer] = {}

        for q_name, q_spec in questions.items():
            q_type = q_spec.get("type", "noul")

            if q_name == "location_compatibility" or q_type == "noul":
                is_remote = "remote" in job_loc or "remote" in job_title or "remote" in job_desc
                loc_matched = any(l in job_loc for l in pref_locs if l != "remote")
                if remote_only:
                    prob = 0.95 if is_remote else 0.05
                elif is_remote or loc_matched:
                    prob = 0.90
                else:
                    prob = 0.15
                answers[q_name] = NoulAnswer(type="noul", noul=prob)

            elif q_name == "seniority_fit" or q_type == "choice":
                # Check for junior / senior indicators
                is_senior_job = any(w in job_title for w in ["senior", "lead", "principal", "staff"])
                is_junior_job = any(w in job_title for w in ["junior", "entry", "intern", "associate"])

                if cand_years >= 4.0:
                    choice = "matched" if is_senior_job or not is_junior_job else "overqualified"
                elif cand_years < 2.0:
                    choice = "underqualified" if is_senior_job else "matched"
                else:
                    choice = "matched"

                answers[q_name] = ChoiceAnswer(
                    type="choice",
                    choice=choice,
                    probabilities={
                        "underqualified": 0.2 if choice != "underqualified" else 0.8,
                        "matched": 0.2 if choice != "matched" else 0.8,
                        "overqualified": 0.2 if choice != "overqualified" else 0.8,
                    },
                )

            elif q_name == "stack_alignment" or q_type == "score":
                overlap_count = sum(
                    1 for skill in primary_skills if skill in job_desc or skill in job_title
                )
                if not primary_skills:
                    score = 1.0
                elif overlap_count >= 2:
                    score = 2.0
                elif overlap_count == 1:
                    score = 1.0
                else:
                    score = 0.0

                probs = [0.1, 0.1, 0.1]
                idx = int(score)
                probs[idx] = 0.8
                answers[q_name] = ScoreAnswer(
                    type="score",
                    score=float(score),
                    probabilities=probs,
                )

        return answers


class OpenRouterDecisionClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "respan/span-01-lite:free",
        app_title: str = "JevScout",
        app_referer: str = "https://github.com/SILICON-HAWK/crawl-mon",
        timeout_seconds: float = 30.0,
    ) -> None:
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY", "")
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY must be provided or set in environment.")
        self.model = model
        self.app_title = app_title
        self.app_referer = app_referer
        self.timeout_seconds = timeout_seconds

    def evaluate(
        self,
        state: Union[str, Dict[str, Any], List[Any]],
        questions: Dict[str, Dict[str, Any]],
        *,
        model: Optional[str] = None,
    ) -> Dict[str, DecisionAnswer]:
        target_model = model or self.model
        payload = {
            "model": target_model,
            "state": state,
            "questions": questions,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-Title": self.app_title,
            "HTTP-Referer": self.app_referer,
        }

        req = urllib.request.Request(
            OPENROUTER_DECISIONS_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as err:
            err_body = err.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"OpenRouter Decisions API returned HTTP {err.code}: {err_body}"
            ) from err
        except urllib.error.URLError as err:
            raise RuntimeError(f"Failed to reach OpenRouter Decisions API: {err.reason}") from err

        raw_answers = data.get("answers", {})
        parsed: Dict[str, DecisionAnswer] = {}

        for name, ans in raw_answers.items():
            ans_type = ans.get("type")
            if ans_type == "noul":
                parsed[name] = NoulAnswer(
                    type="noul",
                    noul=float(ans.get("noul", 0.0)),
                )
            elif ans_type == "choice":
                parsed[name] = ChoiceAnswer(
                    type="choice",
                    choice=str(ans.get("choice", "")),
                    probabilities={
                        k: float(v) for k, v in ans.get("probabilities", {}).items()
                    },
                )
            elif ans_type == "score":
                parsed[name] = ScoreAnswer(
                    type="score",
                    score=float(ans.get("score", 0.0)),
                    probabilities=[float(p) for p in ans.get("probabilities", [])],
                )

        return parsed
