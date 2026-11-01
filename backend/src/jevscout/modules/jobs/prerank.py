"""Structured, model-free pre-ranking of jobs by loose title, salary and location match.

Scores are 0-100 (higher is better). Missing information earns neutral credit so
that sparse feeds are neither rewarded nor buried. This is a cheap triage signal
ahead of the decision model, not a hiring judgement.
"""

from __future__ import annotations

import re
from typing import Any

WEIGHTS = {"title": 0.45, "location": 0.30, "salary": 0.25}
NEUTRAL = 50.0

# Rough, static rates to INR. Deliberately approximate: salary matching is loose.
_INR_PER = {"INR": 1.0, "USD": 84.0, "EUR": 92.0, "GBP": 107.0, "CAD": 61.0, "AUD": 55.0,
            "SGD": 63.0, "AED": 23.0, "CHF": 95.0, "JPY": 0.56, "CNY": 11.7, "MYR": 19.0,
            "KRW": 0.06, "BRL": 15.0, "PLN": 21.0}
_SYMBOLS = {"₹": "INR", "$": "USD", "€": "EUR", "£": "GBP"}

_GENERIC = {"software", "engineer", "developer", "engineering", "senior", "junior", "sr", "jr",
            "lead", "staff", "principal", "associate", "intern", "i", "ii", "iii", "the", "and", "of"}
_PHRASES = re.compile(r"\b(?:artificial intelligence|machine learning|deep learning|generative ai)\b")
_SYNONYMS = {"ml": "ai", "llm": "ai", "genai": "ai", "swe": "engineer", "sde": "engineer",
             "programmer": "developer", "developer": "engineer", "engineers": "engineer",
             "deployment": "deployed", "fde": "deployed", "frontend": "front", "backend": "back"}


def _tokens(text: str) -> list[str]:
    words = re.findall(r"[a-z0-9+#.]+", _PHRASES.sub("ai", text.casefold()))
    return [_SYNONYMS.get(w, w) for w in words if w]


def _title_score(title: Any, role_target: Any) -> tuple[float, str]:
    if not isinstance(title, str) or not title.strip():
        return NEUTRAL, "no title"
    if not isinstance(role_target, str) or not role_target.strip():
        return NEUTRAL, "no target role set"
    wanted = {t for t in _tokens(role_target) if len(t) > 1 or t == "i"}
    have = set(_tokens(title))
    if not wanted:
        return NEUTRAL, "no target role set"
    weight = lambda t: 0.4 if t in _GENERIC else 1.0
    total = sum(weight(t) for t in wanted)
    hit = {t for t in wanted if t in have}
    score = 100.0 * sum(weight(t) for t in hit) / total
    specific = sorted(t for t in hit if t not in _GENERIC)
    note = f"title matches {', '.join(specific)}" if specific else (
        "generic title overlap" if hit else "title unrelated to target")
    return score, note


def _numbers(text: str) -> list[float]:
    return [float(n.replace(",", "")) for n in re.findall(r"\d[\d,]*\.?\d*", text)
            if n.replace(",", "").replace(".", "").isdigit()]


def annual_inr(salary: Any) -> float | None:
    """Best-effort annual INR upper bound from a displayed salary; None when unusable."""
    currency, values, unit = None, [], ""
    if isinstance(salary, dict):
        currency = salary.get("currency")
        values = [v for v in (salary.get("max"), salary.get("maxValue"), salary.get("min"),
                              salary.get("minValue"), salary.get("value"))
                  if isinstance(v, (int, float)) and not isinstance(v, bool)]
        unit = str(salary.get("interval") or salary.get("unitText") or "")
    elif isinstance(salary, (int, float)) and not isinstance(salary, bool):
        values = [float(salary)]
    elif isinstance(salary, str):
        text = salary
        for symbol, code in _SYMBOLS.items():
            if symbol in text:
                currency = currency or code
        found = re.search(r"\b([A-Z]{3})\b", text)
        currency = (found.group(1) if found else None) or currency
        values = _numbers(text)
        unit = text
    if not values or max(values) <= 0:
        return None
    rate = _INR_PER.get(str(currency or "INR").upper())
    if rate is None:
        return None
    amount = max(values) * rate
    unit = unit.casefold()
    if "month" in unit:
        amount *= 12
    elif "hour" in unit:
        amount *= 2000
    return amount


def _salary_score(salary: Any, minimum: Any) -> tuple[float, str]:
    if not isinstance(minimum, (int, float)) or isinstance(minimum, bool) or minimum <= 0:
        return NEUTRAL, "no salary floor set"
    amount = annual_inr(salary)
    if amount is None:
        return NEUTRAL, "salary not disclosed"
    ratio = amount / minimum
    score = max(0.0, min(100.0, (ratio - 0.4) / 0.6 * 100.0))
    return score, ("salary meets your floor" if ratio >= 1 else "salary below your floor")


def _location_score(job: dict, preferred: Any, remote_only: bool) -> tuple[float, str]:
    place = job.get("location")
    place = place.casefold() if isinstance(place, str) else ""
    prefs = [p.casefold().strip() for p in preferred or [] if isinstance(p, str) and p.strip()]
    remote = "remote" in place or "anywhere" in place
    if not place and not job.get("is_india"):
        return NEUTRAL, "location unknown"
    if any(p in place for p in prefs) or (job.get("is_india") and any(p in ("india", "in") for p in prefs)):
        return 100.0, "in a preferred location"
    if remote:
        return (100.0, "remote") if remote_only else (60.0, "remote, outside preferred locations")
    if not prefs and not remote_only:
        return NEUTRAL, "no location preference"
    return 0.0, "outside preferred locations"


def pre_rank(job: dict, profile: dict | None) -> dict:
    """Return the weighted 0-100 ``score``, per-signal scores and short ``reasons``."""
    profile = profile or {}
    title, t_note = _title_score(job.get("title"), profile.get("role_target"))
    place, l_note = _location_score(job, profile.get("preferred_locations"),
                                    bool(profile.get("remote_only")))
    pay, s_note = _salary_score(job.get("salary"), profile.get("min_salary_inr"))
    score = title * WEIGHTS["title"] + place * WEIGHTS["location"] + pay * WEIGHTS["salary"]
    return {"score": round(score, 1), "title": round(title), "salary": round(pay),
            "location": round(place), "reasons": [t_note, l_note, s_note]}
