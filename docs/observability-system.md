# JevScout Observability & Telemetry Architecture

**Status:** Approved Technical Specification & Implementation Blueprint  
**Version:** 1.0.0  
**Target Systems:** JevScout FastAPI Backend, Crawlee Ingestion Engine, Async Workers, OpenRouter LLM Client, Svelte Frontend  
**Audience:** Principal Architects, Systems Engineers, Core Developers  

---

## 1. Executive Summary & Audit Assessment

### 1.1 Context & Problem Statement
A comprehensive observability audit of JevScout revealed severe operational blindspots across ingestion, classification, API serving, and client interactions. In its current state, JevScout operates as an opaque system: failures are masked, logs are either missing or unstructured, exceptions are swallowed, and external API consumption (such as OpenRouter LLM evaluations) lacks financial, performance, and rate-limit visibility.

### 1.2 Summary of Critical Audit Findings

| Component | Audit Finding | Operational Impact | Risk Level |
| :--- | :--- | :--- | :--- |
| **FastAPI Layer (`api.py`)** | Zero correlation IDs (`X-Request-ID`), no request access logging, no timing headers. | Impossible to correlate client issues with server logs or trace requests through asynchronous tasks. | **Critical** |
| **Error Handling (`api.py`, `postgres.py`)** | Systemic `raise ... from None` masking original causes and tracebacks. | Root causes are obliterated from crash reports; debugging requires reproducing production states locally. | **Critical** |
| **Worker Threads (`pipeline.py`, `availability.py`, `operations.py`)** | Bare `except Exception:` swallowing exceptions silently under the guise of secret protection. | Background worker failures hang or terminate silently without alerting operators or logging stack traces. | **Critical** |
| **Ingestion Workers (`parallel_fetch.py`, `feed_refresh.py`)** | Raw `print()` statements throughout ingestion routines instead of leveled logs. | Unparseable logs; cannot be ingested into log aggregators (Elasticsearch, Loki, CloudWatch); unrotated stdout. | **High** |
| **LLM Gateway (`client.py`)** | Complete telemetry blindspot in `OpenRouterDecisionClient` (no latency, tokens, or rate-limit headers). | Unmonitored LLM spend, silent upstream rate-limiting (HTTP 429), unmeasured inference latency and cache performance. | **Critical** |
| **Framework Loggers (`crawlee.py`)** | Silencing loggers globally (`setLevel(logging.CRITICAL)`) instead of redacting sensitive data. | Diagnostic data from Crawlee, HTTPX, and HTTPCore is permanently destroyed, making crawler bugs unfixable. | **High** |
| **Log Storage & Rotation** | No log file persistence, no log rotation policy (`RotatingFileHandler` absent). | Logs are lost on container restart or crash; risk of unbounded disk consumption on bare-metal deployments. | **High** |
| **Frontend (`App.svelte`)** | `fetch` wrapper does not transmit or capture request IDs; errors lack correlation tokens. | Users report errors that cannot be mapped to server-side exceptions. | **Medium** |

### 1.3 Architectural Objectives
1. **Universal Request Tracing:** Establish end-to-end request correlation using standard `X-Request-ID` propagation from the Svelte SPA through FastAPI, background workers, and external service calls.
2. **Standardized Structured JSON Logging:** Guarantee 100% structured JSON logs with a unified schema across all services, workers, and adapters.
3. **In-Flight Secret & PII Redaction:** Implement zero-leakage redaction filters that scrub API keys, tokens, emails, phone numbers, and candidate profile data before log emission without silencing loggers.
4. **Comprehensive LLM Observability:** Instrument `OpenRouterDecisionClient` to track latency, token consumption (prompt/completion), rate-limit budgets (`x-ratelimit-*`), and cache efficiency.
5. **Resilient Failure Logging:** Replace exception swallowing and `raise ... from None` with root-cause preserving structured error logs and clean, sanitized client responses.
6. **Dual-Sink Persistence:** Provide zero-dependency stdout stream for containerized environments alongside a bounded rotating file handler (`10MB x 5 backups`) for local and VM runtimes.

---

## 2. Target Observability Topology & Data Flow

### 2.1 System Observability Architecture
The target observability architecture establishes a decoupled, non-blocking telemetry pipeline where logs, metrics, and tracing metadata flow uniformly across synchronous HTTP paths and asynchronous worker threads.

```mermaid
flowchart TD
    subgraph Client["Client Layer"]
        SPA["Svelte SPA (App.svelte)\n• Injects X-Request-ID\n• Captures Trace ID on Error"]
    end

    subgraph Edge["Ingress & Gateway"]
        LB["Reverse Proxy / Nginx / ALB\n• Preserves/Generates X-Request-ID"]
    end

    subgraph API["FastAPI Application (interfaces/api.py)"]
        TraceMiddleware["Tracing Middleware\n• ContextVar Binding\n• Access Timing (duration_ms)\n• Header Injection"]
        RouteHandlers["Route Handlers\n• /api/pipeline\n• /api/classify\n• /api/availability"]
        GlobalErrHandler["Global Exception Handler\n• Full Traceback Logging\n• Sanitized Error Response"]
    end

    subgraph Context["Telemetry Context Fabric"]
        CV["Python contextvars\n(correlation_id, user_id, run_id)"]
    end

    subgraph Workers["Background & Ingestion Workers"]
        PipeMgr["PipelineManager (pipeline.py)"]
        AvailMgr["AvailabilityManager (availability.py)"]
        ParallelWorker["ParallelFeedFetcher (parallel_fetch.py)"]
        FeedCron["FeedRefreshWorker (feed_refresh.py)"]
    end

    subgraph ExtGateways["External Gateways"]
        ORClient["OpenRouterDecisionClient (scoring/client.py)\n• Latency Tracking\n• Token Accounting\n• Rate-Limit Header Extraction"]
        CrawlerEngine["CrawleeEngine (crawlee.py)\n• Stream Redaction Filter\n• HTTP Status & DNS Metrics"]
    end

    subgraph ObsCore["Observability Core Engine (core/observability.py)"]
        RedactFilter["Automated PII & Secret Redaction Filter"]
        JSONFormatter["Canonical JSON Formatter"]
    end

    subgraph Sinks["Log & Metric Sinks"]
        StdoutSink["stdout (Structured JSON)\n• Docker / Kubernetes / systemd"]
        FileSink["RotatingFileHandler\n• data/logs/jevscout.log (10MB x 5)"]
        MetricsRegistry["In-Memory / Prometheus Metrics\n• Counters, Latency Histograms"]
    end

    %% Flow connections
    SPA -->|"HTTP Request + X-Request-ID"| LB
    LB -->|"Preserved X-Request-ID"| TraceMiddleware
    TraceMiddleware -->|"Set Correlation Context"| CV
    TraceMiddleware --> RouteHandlers
    RouteHandlers -.->|"Unhandled Exception"| GlobalErrHandler
    RouteHandlers -->|"Dispatch Async Task (Propagate Context)"| Workers

    RouteHandlers --> ORClient
    Workers --> ORClient
    Workers --> CrawlerEngine

    CV -.->|"Injects correlation_id"| ObsCore
    RouteHandlers -.->|"Structured Event"| ObsCore
    Workers -.->|"Structured Event"| ObsCore
    ORClient -.->|"LLM Telemetry Event"| ObsCore
    CrawlerEngine -.->|"Crawl Diagnostic Event"| ObsCore

    ObsCore --> RedactFilter
    RedactFilter --> JSONFormatter
    JSONFormatter --> StdoutSink
    JSONFormatter --> FileSink
    ORClient -.->|"Export Metrics"| MetricsRegistry
    TraceMiddleware -.->|"Export Metrics"| MetricsRegistry
```

### 2.2 Telemetry Data Flow Sequence
1. **Client Ingress:** The Svelte SPA generates or propagates a unique `X-Request-ID` via `crypto.randomUUID()`.
2. **Context Binding:** The FastAPI ASGI middleware captures or creates the `correlation_id` and stores it in an asynchronous context variable (`contextvars.ContextVar`).
3. **Execution & Log Emission:** All log calls (`logger.info`, `logger.error`) within that request execution thread or asynchronous task automatically pull the active `correlation_id` without requiring manual parameter passing.
4. **Worker Context Propagation:** When background threads (`threading.Thread`) or async tasks (`asyncio.create_task`) are spawned (e.g., in `PipelineManager` or `AvailabilityManager`), the correlation context is explicitly captured and copied into the worker scope.
5. **External LLM Call:** The `OpenRouterDecisionClient` measures request latency via high-precision monotonic clock (`time.perf_counter()`), parses token counts and rate-limit headers from OpenRouter responses, and logs an enriched telemetry event bound to the correlation ID.
6. **In-Flight Scrubbing & Dual-Sink Serialization:** All log records pass through the `PIIRedactionFilter`, which executes recursive mask patterns across data payloads and message strings before the `JSONFormatter` serializes the record to `stdout` and `jevscout.log`.

---

## 3. Canonical Telemetry & Log Schema Specification

### 3.1 JSON Log Schema Definition
Every log record emitted across JevScout must be valid JSON conforming to the following canonical schema:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "JevScoutLogEvent",
  "type": "object",
  "required": [
    "timestamp",
    "level",
    "logger",
    "event",
    "service",
    "correlation_id"
  ],
  "properties": {
    "timestamp": {
      "type": "string",
      "format": "date-time",
      "description": "ISO 8601 UTC timestamp with millisecond precision (e.g. 2026-11-01T21:40:12.345Z)"
    },
    "level": {
      "type": "string",
      "enum": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    },
    "logger": {
      "type": "string",
      "description": "Python logger namespace (e.g. jevscout.interfaces.api)"
    },
    "service": {
      "type": "string",
      "description": "Subsystem identifier: jevscout-api, jevscout-worker, jevscout-crawler, or jevscout-llm"
    },
    "correlation_id": {
      "type": "string",
      "description": "UUIDv4 correlation identifier linking related events across components"
    },
    "event": {
      "type": "string",
      "description": "Machine-readable dot-notated event name (e.g. http.request.completed, llm.decision.completed)"
    },
    "duration_ms": {
      "type": "number",
      "description": "Execution duration in milliseconds (floating-point precision)"
    },
    "http": {
      "type": "object",
      "properties": {
        "method": { "type": "string" },
        "route": { "type": "string" },
        "status_code": { "type": "integer" },
        "client_ip": { "type": "string" },
        "user_agent": { "type": "string" }
      }
    },
    "llm": {
      "type": "object",
      "properties": {
        "provider": { "type": "string" },
        "model": { "type": "string" },
        "prompt_tokens": { "type": "integer" },
        "completion_tokens": { "type": "integer" },
        "total_tokens": { "type": "integer" },
        "cache_hit": { "type": "boolean" },
        "rate_limit_remaining": { "type": "integer" },
        "rate_limit_reset_seconds": { "type": "number" }
      }
    },
    "worker": {
      "type": "object",
      "properties": {
        "task_name": { "type": "string" },
        "task_id": { "type": "string" },
        "feed_name": { "type": "string" },
        "provider": { "type": "string" },
        "items_extracted": { "type": "integer" },
        "pages_saved": { "type": "integer" }
      }
    },
    "error": {
      "type": "object",
      "properties": {
        "type": { "type": "string" },
        "message": { "type": "string" },
        "code": { "type": "string" },
        "stack_trace": { "type": "string" }
      }
    },
    "context": {
      "type": "object",
      "description": "Arbitrary structured key-value metadata specific to the operation"
    }
  }
}
```

### 3.2 Canonical Event Taxonomy
Standardizing event names allows instant metric aggregation and dashboarding:

| Namespace | Event Name | When Emitted | Key Attributes |
| :--- | :--- | :--- | :--- |
| **HTTP** | `http.request.started` | Route middleware entry | `http.method`, `http.route`, `http.client_ip` |
| | `http.request.completed` | Response return | `http.status_code`, `duration_ms` |
| | `http.request.failed` | Unhandled route error | `http.status_code`, `error.*`, `duration_ms` |
| **LLM** | `llm.decision.started` | OpenRouter dispatch | `llm.model`, `questions_count` |
| | `llm.decision.completed` | Successful evaluation | `duration_ms`, `llm.total_tokens`, `llm.rate_limit_remaining` |
| | `llm.decision.cached` | Local/saved match reuse | `llm.cache_hit=true`, `duration_ms` |
| | `llm.decision.failed` | Upstream HTTP error/timeout | `error.*`, `duration_ms`, `status_code` |
| **Worker** | `worker.sweep.started` | Ingestion sweep initiation | `worker.task_name`, `feed_count` |
| | `worker.feed.completed` | Individual feed scrape success | `worker.feed_name`, `worker.items_extracted`, `duration_ms` |
| | `worker.feed.failed` | Individual feed failure | `worker.feed_name`, `error.*` |
| | `worker.sweep.completed` | Sweep summary | `total_items`, `duration_ms`, `success_rate` |
| **Availability** | `availability.batch.started` | Batch URL verification | `batch_size` |
| | `availability.check.completed`| Single URL verified | `target_url_host`, `status_code`, `state` |
| | `availability.batch.completed`| Batch check finished | `duration_ms`, `available_count`, `unavailable_count` |

---

## 4. Standardized Structured Logging & Redaction Engine

Below is the concrete, production-grade implementation of `jevscout.core.observability`. It requires only Python standard library components (`logging`, `json`, `re`, `contextvars`, `time`, `pathlib`), guaranteeing immediate deployment without dependency conflicts.

### 4.1 Implementation: `backend/src/jevscout/core/observability.py`

```python
"""Enterprise-grade structured logging, context propagation, and PII redaction engine.

Provides zero-overhead contextvars tracing, canonical JSON serialization,
comprehensive secret/PII filtering, and dual-sink logging (stdout + rotating file).
"""

from __future__ import annotations

import contextvars
import json
import logging
import logging.handlers
import os
import re
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Union

# ---------------------------------------------------------------------------
# Context Variable Registry
# ---------------------------------------------------------------------------

_correlation_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar(
    "correlation_id", default="system-unassigned"
)
_user_id_ctx: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "user_id", default=None
)
_run_id_ctx: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "run_id", default=None
)


def get_correlation_id() -> str:
    """Retrieve the current asynchronous context's correlation ID."""
    return _correlation_id_ctx.get()


def set_correlation_id(correlation_id: str) -> contextvars.Token:
    """Set the correlation ID for the active asynchronous context."""
    return _correlation_id_ctx.set(correlation_id)


def reset_correlation_id(token: contextvars.Token) -> None:
    """Reset the correlation ID using the previous context token."""
    _correlation_id_ctx.reset(token)


def get_telemetry_context() -> Dict[str, Any]:
    """Return all active contextual attributes for logging enrichment."""
    ctx: Dict[str, Any] = {"correlation_id": _correlation_id_ctx.get()}
    user_id = _user_id_ctx.get()
    if user_id:
        ctx["user_id"] = user_id
    run_id = _run_id_ctx.get()
    if run_id:
        ctx["run_id"] = run_id
    return ctx


# ---------------------------------------------------------------------------
# PII & Secret Redaction Engine
# ---------------------------------------------------------------------------

# Sensitive dictionary keys to immediately mask
SENSITIVE_KEYS = frozenset({
    "authorization",
    "proxy-authorization",
    "x-api-key",
    "openrouter_api_key",
    "api_key",
    "apikey",
    "secret",
    "password",
    "token",
    "access_token",
    "refresh_token",
    "private_key",
    "cookie",
    "set-cookie",
})

# Regular expressions for scrubbing string fields and unstructured tracebacks
REDACTION_PATTERNS = [
    # Bearer tokens & generic auth headers
    (re.compile(r"(Bearer\s+)[A-Za-z0-9_\-\.]{8,}", re.IGNORECASE), r"\1[REDACTED_TOKEN]"),
    # OpenRouter API Keys (sk-or-v1-...)
    (re.compile(r"sk-or-v1-[a-f0-9]{64}", re.IGNORECASE), "sk-or-v1-[REDACTED_API_KEY]"),
    # Generic API Keys / Secrets in query params or text (api_key=...)
    (re.compile(r"((?:api[_-]?key|secret|token|password)=)[^\s&\"']+", re.IGNORECASE), r"\1[REDACTED]"),
    # PostgreSQL / DB connection credentials: postgres://user:password@host
    (re.compile(r"(postgres(?:ql)?:\/\/[^:]+:)[^@]+(@)", re.IGNORECASE), r"\1[REDACTED_PASSWORD]\2"),
    # Email addresses (Candidate profile PII)
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"), "[REDACTED_EMAIL]"),
    # Phone numbers (E.164 and common candidate resume formats)
    (re.compile(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"), "[REDACTED_PHONE]"),
]


def redact_text(text: str) -> str:
    """Apply regex masks to sensitive string patterns."""
    if not isinstance(text, str):
        return text
    redacted = text
    for pattern, replacement in REDACTION_PATTERNS:
        redacted = pattern.sub(replacement, redacted)
    return redacted


def redact_data(obj: Any) -> Any:
    """Recursively scrub sensitive keys and patterns from dictionaries and lists."""
    if isinstance(obj, dict):
        cleaned: Dict[str, Any] = {}
        for k, v in obj.items():
            if str(k).lower() in SENSITIVE_KEYS:
                cleaned[k] = "[REDACTED_SECRET]"
            else:
                cleaned[k] = redact_data(v)
        return cleaned
    elif isinstance(obj, list):
        return [redact_data(item) for item in obj]
    elif isinstance(obj, str):
        return redact_text(obj)
    return obj


class PIIRedactionFilter(logging.Filter):
    """Logging filter that scrubs secrets and PII in-place from log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        # Scrub message string
        if isinstance(record.msg, str):
            record.msg = redact_text(record.msg)
        
        # Scrub formatting arguments
        if record.args:
            if isinstance(record.args, dict):
                record.args = redact_data(record.args)
            elif isinstance(record.args, (list, tuple)):
                record.args = tuple(redact_data(a) for a in record.args)
        
        # Scrub custom contextual attributes attached to the LogRecord
        for attr in ("context", "http", "llm", "worker", "error"):
            if hasattr(record, attr):
                setattr(record, attr, redact_data(getattr(record, attr)))

        return True


# ---------------------------------------------------------------------------
# Canonical Structured JSON Formatter
# ---------------------------------------------------------------------------

class StructuredJSONFormatter(logging.Formatter):
    """Serializes log records into canonical JevScout JSON schema format."""

    def __init__(self, service_name: str = "jevscout-core") -> None:
        super().__init__()
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        now = datetime.now(timezone.utc)
        timestamp_str = now.isoformat().replace("+00:00", "Z")

        # Pull correlation and context attributes
        correlation_id = getattr(record, "correlation_id", None) or get_correlation_id()
        event_name = getattr(record, "event", None) or record.getMessage()

        payload: Dict[str, Any] = {
            "timestamp": timestamp_str,
            "level": record.levelname,
            "logger": record.name,
            "service": getattr(record, "service", self.service_name),
            "correlation_id": correlation_id,
            "event": event_name,
        }

        # Optional duration
        if hasattr(record, "duration_ms"):
            payload["duration_ms"] = round(float(record.duration_ms), 3)

        # Domain metadata blocks
        for domain_block in ("http", "llm", "worker", "context"):
            if hasattr(record, domain_block):
                payload[domain_block] = getattr(record, domain_block)

        # Exception & traceback capture
        if record.exc_info:
            exc_type, exc_val, exc_tb = record.exc_info
            stack = "".join(traceback.format_exception(exc_type, exc_val, exc_tb))
            payload["error"] = {
                "type": exc_type.__name__ if exc_type else "Exception",
                "message": redact_text(str(exc_val)),
                "stack_trace": redact_text(stack),
            }
        elif hasattr(record, "error"):
            payload["error"] = getattr(record, "error")

        return json.dumps(payload, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Logging Subsystem Initializer
# ---------------------------------------------------------------------------

def configure_observability(
    service_name: str = "jevscout-api",
    log_dir: Optional[Union[str, Path]] = None,
    log_level: int = logging.INFO,
    enable_console: bool = True,
    enable_file: bool = True,
    max_bytes: int = 10 * 1024 * 1024,  # 10 MB per file
    backup_count: int = 5,              # 5 rotated archives (60 MB total ceiling)
) -> None:
    """Configure unified root logger with dual sinks, JSON formatter, and redaction.

    Safe to invoke multiple times (idempotent).
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Clear existing handlers to prevent duplicate output
    root_logger.handlers.clear()

    redaction_filter = PIIRedactionFilter()
    formatter = StructuredJSONFormatter(service_name=service_name)

    # 1. Console / stdout Sink (Docker / Cloud / systemd)
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.addFilter(redaction_filter)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    # 2. Rotating File Sink (Local / VM Persistence)
    if enable_file:
        target_dir = Path(log_dir) if log_dir else Path("data/logs")
        target_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        log_file = target_dir / "jevscout.log"

        # Safe cross-platform rotating file handler
        file_handler = logging.handlers.RotatingFileHandler(
            filename=str(log_file),
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
            delay=True,
        )
        file_handler.setLevel(log_level)
        file_handler.addFilter(redaction_filter)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Adjust external framework loggers: do NOT silence, set to WARNING to capture issues
    for fw_name in ("crawlee", "httpx2", "httpcore2", "uvicorn", "uvicorn.access"):
        fw_logger = logging.getLogger(fw_name)
        fw_logger.setLevel(logging.WARNING)
        fw_logger.propagate = True
```

---

## 5. FastAPI Request Tracing Middleware & Error Handling

### 5.1 Architecture & Requirements
1. **Correlation Extraction & Propagation:** The middleware inspects incoming HTTP request headers for `X-Request-ID`. If absent or malformed (non-UUID), a standard UUIDv4 is generated.
2. **Context Binding:** The ID is immediately bound to `_correlation_id_ctx` using Python `contextvars`.
3. **Response Header Guarantee:** Every HTTP response leaving the server includes the `X-Request-ID` header.
4. **Access Timing & Structured Access Log:** Upon response generation, an `http.request.completed` log event is recorded with method, route, status code, client IP, user agent, and millisecond duration.
5. **Global Exception Handling:** Replaces all `raise ... from None` with an ASGI-level exception handler that logs the full traceback with the correlation ID, returning a standardized HTTP 500 payload containing the correlation ID so users can quote it in support queries.

### 5.2 Implementation Blueprint: Tracing Middleware & Handlers

```python
"""FastAPI ASGI Tracing Middleware and Global Exception Handlers.

Integrates with jevscout.core.observability to provide request timing,
correlation headers, and stack-trace-preserving error responses.
"""

from __future__ import annotations

import time
import uuid
from typing import Callable
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import logging

from jevscout.core.observability import (
    get_correlation_id,
    set_correlation_id,
    reset_correlation_id,
)

logger = logging.getLogger("jevscout.interfaces.api")


class CorrelationTracingMiddleware(BaseHTTPMiddleware):
    """ASGI Middleware that manages request correlation IDs and access logging."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.perf_counter()

        # 1. Extract or generate X-Request-ID
        raw_id = request.headers.get("X-Request-ID", "").strip()
        if raw_id and len(raw_id) <= 128:
            correlation_id = raw_id
        else:
            correlation_id = str(uuid.uuid4())

        # 2. Bind to asynchronous context
        token = set_correlation_id(correlation_id)

        # Extract client IP safely (respecting reverse proxy X-Forwarded-For if present)
        forwarded_for = request.headers.get("X-Forwarded-For")
        client_ip = (
            forwarded_for.split(",")[0].strip()
            if forwarded_for
            else (request.client.host if request.client else "unknown")
        )

        http_info = {
            "method": request.method,
            "route": request.url.path,
            "client_ip": client_ip,
            "user_agent": request.headers.get("User-Agent", "unknown"),
        }

        try:
            response: Response = await call_next(request)
            duration_ms = (time.perf_counter() - start_time) * 1000.0

            # Attach tracing header to outgoing response
            response.headers["X-Request-ID"] = correlation_id

            # Emit structured access log
            logger.info(
                f"{request.method} {request.url.path} -> {response.status_code} ({duration_ms:.1f}ms)",
                extra={
                    "event": "http.request.completed",
                    "duration_ms": duration_ms,
                    "correlation_id": correlation_id,
                    "http": {**http_info, "status_code": response.status_code},
                },
            )
            return response

        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            logger.error(
                f"Unhandled error in {request.method} {request.url.path}: {exc}",
                exc_info=True,
                extra={
                    "event": "http.request.failed",
                    "duration_ms": duration_ms,
                    "correlation_id": correlation_id,
                    "http": {**http_info, "status_code": 500},
                },
            )
            # Re-raise to trigger global exception handler
            raise
        finally:
            reset_correlation_id(token)


def register_observability_handlers(app: FastAPI) -> None:
    """Attach correlation middleware and global error handlers to FastAPI app."""
    app.add_middleware(CorrelationTracingMiddleware)

    @app.exception_handler(Exception)
    async def global_unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        correlation_id = get_correlation_id()
        # Full stack trace is already logged in middleware
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "message": "An unexpected error occurred during request processing.",
                "correlation_id": correlation_id,
            },
            headers={"X-Request-ID": correlation_id},
        )
```

---

## 6. LLM & External Gateway Telemetry

### 6.1 Telemetry Objectives for OpenRouter
The current `OpenRouterDecisionClient` executes critical inference without tracking latency, token usage, rate limits, or caching. To make this production-ready, we introduce the `InstrumentedDecisionClient` decorator/wrapper that observes:
1. **Wall-clock inference latency** with microsecond precision.
2. **Token accounting:** Extracting `usage.prompt_tokens`, `usage.completion_tokens`, and `usage.total_tokens` from response payloads.
3. **OpenRouter Rate-Limit Headers:** Parsing `x-ratelimit-limit`, `x-ratelimit-remaining`, and `x-ratelimit-reset` from the HTTP response headers.
4. **Cache Telemetry:** Distinguishing between network inference and local cache hits.
5. **Upstream Failure Reporting:** Detailed HTTP error logging with correlation IDs, without exposing raw user profile context in error traces.

### 6.2 Implementation: Telemetry-Enriched LLM Gateway

```python
"""Instrumented OpenRouter Decision Client with full telemetry.

Captures latency, token counts, rate-limit headers, and cache events.
"""

from __future__ import annotations

import json
import logging
import os
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Union

from jevscout.core.observability import get_correlation_id
from jevscout.modules.jobs.scoring.models import (
    ChoiceAnswer,
    DecisionAnswer,
    NoulAnswer,
    ScoreAnswer,
)

logger = logging.getLogger("jevscout.modules.jobs.scoring.client")

OPENROUTER_DECISIONS_URL = "https://openrouter.ai/api/alpha/decisions"


class InstrumentedOpenRouterDecisionClient:
    """Production-grade OpenRouter client featuring comprehensive telemetry."""

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
        correlation_id = get_correlation_id()
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
            "X-Correlation-ID": correlation_id,
        }

        req = urllib.request.Request(
            OPENROUTER_DECISIONS_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )

        start_time = time.perf_counter()
        logger.debug(
            "Initiating OpenRouter decision request",
            extra={
                "event": "llm.decision.started",
                "correlation_id": correlation_id,
                "llm": {"provider": "openrouter", "model": target_model, "questions_count": len(questions)},
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                raw_bytes = resp.read()
                duration_ms = (time.perf_counter() - start_time) * 1000.0
                data = json.loads(raw_bytes.decode("utf-8"))

                # Extract OpenRouter rate limit telemetry from HTTP response headers
                resp_headers = resp.headers
                rl_limit = resp_headers.get("x-ratelimit-limit")
                rl_remaining = resp_headers.get("x-ratelimit-remaining")
                rl_reset = resp_headers.get("x-ratelimit-reset")

                usage = data.get("usage", {})
                prompt_tokens = usage.get("prompt_tokens", 0)
                completion_tokens = usage.get("completion_tokens", 0)
                total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)

                logger.info(
                    f"OpenRouter decision completed in {duration_ms:.1f}ms (model={target_model}, tokens={total_tokens})",
                    extra={
                        "event": "llm.decision.completed",
                        "duration_ms": duration_ms,
                        "correlation_id": correlation_id,
                        "llm": {
                            "provider": "openrouter",
                            "model": target_model,
                            "prompt_tokens": prompt_tokens,
                            "completion_tokens": completion_tokens,
                            "total_tokens": total_tokens,
                            "cache_hit": False,
                            "rate_limit_limit": int(rl_limit) if rl_limit and rl_limit.isdigit() else None,
                            "rate_limit_remaining": int(rl_remaining) if rl_remaining and rl_remaining.isdigit() else None,
                            "rate_limit_reset_seconds": float(rl_reset) if rl_reset else None,
                        },
                    },
                )

        except urllib.error.HTTPError as err:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            err_body = err.read().decode("utf-8", errors="replace")
            logger.error(
                f"OpenRouter API HTTP {err.code} error: {err.reason}",
                extra={
                    "event": "llm.decision.failed",
                    "duration_ms": duration_ms,
                    "correlation_id": correlation_id,
                    "llm": {"provider": "openrouter", "model": target_model},
                    "error": {"type": "HTTPError", "code": str(err.code), "message": err_body},
                },
            )
            raise RuntimeError(f"OpenRouter Decisions API returned HTTP {err.code}: {err_body}") from err

        except urllib.error.URLError as err:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            logger.error(
                f"OpenRouter network connectivity failure: {err.reason}",
                extra={
                    "event": "llm.decision.failed",
                    "duration_ms": duration_ms,
                    "correlation_id": correlation_id,
                    "llm": {"provider": "openrouter", "model": target_model},
                    "error": {"type": "URLError", "message": str(err.reason)},
                },
            )
            raise RuntimeError(f"Failed to reach OpenRouter Decisions API: {err.reason}") from err

        # Parse answers
        raw_answers = data.get("answers", {})
        parsed: Dict[str, DecisionAnswer] = {}
        for name, ans in raw_answers.items():
            ans_type = ans.get("type")
            if ans_type == "noul":
                parsed[name] = NoulAnswer(type="noul", noul=float(ans.get("noul", 0.0)))
            elif ans_type == "choice":
                parsed[name] = ChoiceAnswer(
                    type="choice",
                    choice=str(ans.get("choice", "")),
                    probabilities={k: float(v) for k, v in ans.get("probabilities", {}).items()},
                )
            elif ans_type == "score":
                parsed[name] = ScoreAnswer(
                    type="score",
                    score=float(ans.get("score", 0.0)),
                    probabilities=[float(p) for p in ans.get("probabilities", [])],
                )

        return parsed
```

---

## 7. Background Worker & Ingestion Observability

### 7.1 Deficiencies to Resolve
1. **Raw `print()` Statements:** In `parallel_fetch.py` and `feed_refresh.py`, workers output unstructured ASCII text (`[*] Starting...`, `[✓] Ashby...`). This cannot be ingested into centralized log aggregators or monitored for errors.
2. **Silent Exception Swallowing:** In `pipeline.py`, `availability.py`, and `operations.py`, exceptions are caught with bare `except Exception:` blocks, setting status to `"failed"` without logging the stack trace or root cause.
3. **Framework Logger Muting:** In `crawlee.py`, framework loggers are forced to `CRITICAL`, eliminating visibility into HTTP client connection pool errors, DNS resolution failures, and robots.txt denials.

### 7.2 Standardized Worker Logging Pattern

#### 7.2.1 Parallel Fetch Worker (`parallel_fetch.py`)
Replace all raw `print()` statements with structured logger calls:

```python
# Before (anti-pattern):
print(f"[{datetime.now().strftime('%H:%M:%S')}] ✓ [{r.provider}] {r.key}: {r.items_extracted} jobs extracted")
print(f"[{datetime.now().strftime('%H:%M:%S')}] ✗ [{r.provider}] {r.key} failed: {r.error}")

# After (production standard):
if r.status == "completed":
    logger.info(
        f"Feed {r.key} ({r.provider}) completed: {r.items_extracted} jobs",
        extra={
            "event": "worker.feed.completed",
            "duration_ms": r.duration_seconds * 1000.0,
            "worker": {
                "task_name": "parallel_fetch",
                "feed_name": r.key,
                "provider": r.provider,
                "run_id": r.run_id,
                "items_extracted": r.items_extracted,
            },
        },
    )
elif r.status == "failed":
    logger.error(
        f"Feed {r.key} ({r.provider}) failed: {r.error}",
        extra={
            "event": "worker.feed.failed",
            "duration_ms": r.duration_seconds * 1000.0,
            "worker": {
                "task_name": "parallel_fetch",
                "feed_name": r.key,
                "provider": r.provider,
                "run_id": r.run_id,
            },
            "error": {"type": "FeedCollectionError", "message": str(r.error)},
        },
    )
```

#### 7.2.2 Pipeline Worker (`pipeline.py`)
Replace bare exception swallowing with structured error logging while preserving worker isolation:

```python
# Refactored pipeline execution block with resilient structured logging:
try:
    finished = asyncio.run(execute_run(
        self.store, run.id, approved=True, engine=self.engine,
    ))
    # ... process results ...
except Exception as exc:
    any_failure = True
    logger.error(
        f"Pipeline seed execution failed for {seed}: {exc}",
        exc_info=True,
        extra={
            "event": "pipeline.seed.failed",
            "worker": {
                "task_name": "pipeline_execution",
                "pipeline_id": pipeline_id,
                "run_id": run.id,
                "seed_url": seed,
            },
            "error": {
                "type": type(exc).__name__,
                "message": str(exc),
            },
        },
    )
    item = {"run_id": run.id, "seed_url": seed, "status": "failed",
            "pages_saved": 0, "items_found": 0}
```

#### 7.2.3 Availability Manager (`availability.py`)
Ensure background listing verification records start, progress, and failure events:

```python
def work():
    try:
        async def execute():
            checker = AvailabilityChecker(self.store)
            for url in urls:
                check_res = await checker.check([url], requested=True)
                with self._mutex:
                    self._state['completed'] += 1
                logger.debug(
                    f"Verified listing availability for {url}",
                    extra={
                        "event": "availability.check.completed",
                        "context": {"url": url, "state": getattr(check_res, "state", "unknown")},
                    },
                )
                await asyncio.sleep(1)
        asyncio.run(execute())
        with self._mutex:
            self._state['status'] = 'completed'
        logger.info(
            f"Availability check batch completed ({len(urls)} URLs)",
            extra={
                "event": "availability.batch.completed",
                "context": {"total_urls": len(urls), "status": "completed"},
            },
        )
    except Exception as exc:
        with self._mutex:
            self._state['status'] = 'failed'
        logger.error(
            f"Availability verification worker crashed: {exc}",
            exc_info=True,
            extra={
                "event": "availability.batch.failed",
                "error": {"type": type(exc).__name__, "message": str(exc)},
            },
        )
    finally:
        fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
        lock.close()
```

#### 7.2.4 Crawlee Logger Integration (`crawlee.py`)
Remove `logger.setLevel(logging.CRITICAL)` and `quiet_logger = logging.Logger(..., CRITICAL)`. Instead, route framework logs through the standard root logger hierarchy with `WARNING` threshold and the `PIIRedactionFilter`:

```python
# Replaced anti-pattern:
# Previous: forced loggers to logging.CRITICAL, hiding all framework errors.
# Target: Set framework loggers to WARNING and attach PIIRedactionFilter.

def configure_crawlee_logging():
    """Ensure crawling framework logs warnings and errors without leaking sensitive URLs."""
    for name in ("crawlee", "httpx2", "httpcore2"):
        fw_logger = logging.getLogger(name)
        fw_logger.setLevel(logging.WARNING)
        fw_logger.addFilter(PIIRedactionFilter())
```

---

## 8. Log Storage, Retention, and Rotation Policy

### 8.1 Dual-Sink Configuration Specifications
Production environments require dual-sink logging to accommodate both modern containerized orchestrators and traditional bare-metal/local deployments:

1. **Stdout Sink (StreamHandler):**
   - **Target:** Standard output (`sys.stdout`).
   - **Format:** Unbuffered, single-line structured JSON.
   - **Consumer:** Docker logging driver, Kubernetes DaemonSet (FluentBit/Promtail), AWS CloudWatch Container Insights, or systemd-journald.
   - **Retention:** Delegated to the cluster log forwarder or container runtime log rotation policy (`max-size: 50m`, `max-file: 3`).

2. **Persistent File Sink (RotatingFileHandler):**
   - **Target:** `<JEVSCOUT_DATA_DIR>/logs/jevscout.log` (Default: `data/live-trial/logs/jevscout.log` or `data/logs/jevscout.log`).
   - **Format:** Canonical single-line structured JSON (one JSON object per line).
   - **File Size Ceiling:** Exactly **10 MB** (`10 * 1024 * 1024` bytes).
   - **Backup Retention:** **5 rotated backup files** (`jevscout.log.1` through `jevscout.log.5`).
   - **Total Storage Bound:** Maximum 60 MB allocated to logs across all rotations, preventing host disk exhaustion.
   - **Filesystem Permissions:** Directory created with `0o700` (`rwx------`), log files restricted to owner-read/write `0o600` (`rw-------`).

### 8.2 Log File Hierarchy
```
data/
└── logs/
    ├── jevscout.log        (active write sink, max 10MB)
    ├── jevscout.log.1      (most recent rotation)
    ├── jevscout.log.2      (older rotation)
    ├── jevscout.log.3
    ├── jevscout.log.4
    └── jevscout.log.5      (oldest rotation before eviction)
```

---

## 9. Frontend Telemetry & Error Correlation (`App.svelte`)

### 9.1 Requirements
1. **Request ID Injection:** The frontend must generate a UUIDv4 on outgoing API calls and send it in the `X-Request-ID` HTTP header.
2. **Response Header Capture:** The frontend must inspect response headers for `X-Request-ID` and record it.
3. **Correlation in UI:** When an error occurs (network failure, 4xx, 5xx), the UI must display a user-friendly error message accompanied by a distinct, copyable `Reference ID: <request_id>`. This allows users to report exact request tokens to developers for instant log querying.

### 9.2 Frontend Implementation (`frontend/src/App.svelte`)

#### 9.2.1 Upgraded `request()` Utility Function
Replace lines 152–159 of `frontend/src/App.svelte` with:

```javascript
  // Generate RFC4122 v4 UUID with fallback for older environments
  function generateRequestId() {
    if (typeof crypto !== 'undefined' && crypto.randomUUID) {
      return crypto.randomUUID();
    }
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
      const r = (Math.random() * 16) | 0;
      const v = c === 'x' ? r : (r & 0x3) | 0x8;
      return v.toString(16);
    });
  }

  async function request(path, options = {}) {
    const clientRequestId = generateRequestId();
    const headers = {
      'Content-Type': 'application/json',
      'X-Request-ID': clientRequestId,
      ...options.headers,
    };

    let response;
    try {
      response = await fetch(path, { ...options, headers });
    } catch (networkErr) {
      console.error(`[Telemetry] Network dispatch error for ${path} [ReqID: ${clientRequestId}]:`, networkErr);
      const err = new Error(`Network failure connecting to ${path}. Please check your connection.`);
      err.requestId = clientRequestId;
      throw err;
    }

    const serverRequestId = response.headers.get('X-Request-ID') || clientRequestId;
    const raw = await response.text();
    let payload;
    try {
      payload = raw ? JSON.parse(raw) : null;
    } catch {
      payload = raw;
    }

    if (!response.ok) {
      const errorMsg = payload?.detail ?? payload?.message ?? `${response.status} ${response.statusText}`;
      console.error(`[Telemetry] API Error ${response.status} on ${path} [ReqID: ${serverRequestId}]:`, payload);
      const err = new Error(errorMsg);
      err.status = response.status;
      err.requestId = serverRequestId;
      err.payload = payload;
      throw err;
    }

    return payload;
  }
```

#### 9.2.2 User-Facing Error Display Pattern
Whenever an error state is rendered in Svelte components, attach the correlation ID badge:

```svelte
{#if error}
  <div class="p-4 mb-4 text-sm text-red-800 rounded-lg bg-red-50 border border-red-200" role="alert">
    <div class="font-medium flex items-center justify-between">
      <span>Error: {error.message || error}</span>
      {#if error.requestId}
        <span class="text-xs bg-red-100 text-red-700 px-2 py-1 rounded font-mono select-all">
          Ref: {error.requestId}
        </span>
      {/if}
    </div>
  </div>
{/if}
```

---

## 10. Phased Implementation & Verification Plan

### 10.1 Implementation Phases

```mermaid
flowchart LR
    P1["Phase 1:\nCore Logging &\nRedaction Engine"] --> P2["Phase 2:\nFastAPI Middleware\n& Error Handlers"]
    P2 --> P3["Phase 3:\nOpenRouter LLM\nTelemetry Wrapper"]
    P3 --> P4["Phase 4:\nBackground Workers\n& Exception Cleanup"]
    P4 --> P5["Phase 5:\nFrontend Correlation\n& Verification"]
```

#### Phase 1: Core Observability Engine
- Create `backend/src/jevscout/core/observability.py`.
- Implement `PIIRedactionFilter`, `StructuredJSONFormatter`, context variable managers, and `configure_observability()`.
- Add test suite `backend/tests/core/test_observability.py` validating JSON conformance, regex masking, and context variable propagation across threads.

#### Phase 2: FastAPI Tracing & Exception Handling
- Update `backend/src/jevscout/interfaces/api.py`.
- Insert `CorrelationTracingMiddleware` and register `global_unhandled_exception_handler`.
- Remove all `raise ... from None` anti-patterns; preserve inner exception tracebacks while returning sanitized HTTP 500 JSON.
- Add test suite `backend/tests/api/test_observability_middleware.py` verifying `X-Request-ID` propagation and error response schemas.

#### Phase 3: OpenRouter LLM Gateway Instrumentation
- Update `backend/src/jevscout/modules/jobs/scoring/client.py`.
- Wrap `OpenRouterDecisionClient.evaluate` with latency measurement, token accounting, and `x-ratelimit-*` header extraction.
- Verify structured log output during live and mock decision executions.

#### Phase 4: Worker Modernization & Redaction Cleanup
- Modernize `backend/src/jevscout/application/parallel_fetch.py`: replace all `print()` with `logger.info` and `logger.error`.
- Modernize `backend/src/jevscout/application/feed_refresh.py`: replace all `print()` with structured events.
- Modernize `backend/src/jevscout/application/pipeline.py` and `availability.py`: replace bare `except Exception:` blocks with structured error logging.
- Update `backend/src/jevscout/adapters/crawling/crawlee.py`: remove logger silencing and route framework logs through `PIIRedactionFilter`.

#### Phase 5: Frontend Correlation & End-to-End Validation
- Update `frontend/src/App.svelte` request utility to inject and capture `X-Request-ID`.
- Update error presentation in Svelte UI to display reference IDs.
- Execute full test matrix.

---

### 10.2 Comprehensive Verification Test Matrix

| Test ID | Target Component | Verification Scenario | Success Criteria |
| :--- | :--- | :--- | :--- |
| **TC-OBS-01** | `observability.py` | Secret redaction: log Bearer token, OpenRouter key, and candidate email. | Log output masks tokens as `[REDACTED_TOKEN]`, `[REDACTED_EMAIL]`, etc. |
| **TC-OBS-02** | `observability.py` | Rotating file handler: generate 15 MB of logs in test environment. | Active file stays $\le 10\text{ MB}$; `jevscout.log.1` created; file count $\le 6$. |
| **TC-OBS-03** | `api.py` | Inbound request without `X-Request-ID`. | Response contains valid UUIDv4 `X-Request-ID`; stdout log includes identical correlation ID. |
| **TC-OBS-04** | `api.py` | Inbound request with custom `X-Request-ID: test-trace-999`. | Outbound response and all associated log records reflect `test-trace-999`. |
| **TC-OBS-05** | `api.py` | Unhandled route exception simulation. | Full stack trace logged at `ERROR` level; client receives HTTP 500 with matching `correlation_id`. |
| **TC-OBS-06** | `client.py` | OpenRouter evaluation execution (mock & live). | Telemetry log contains `duration_ms`, `llm.prompt_tokens`, and `llm.rate_limit_remaining`. |
| **TC-OBS-07** | `parallel_fetch.py`| Parallel sweep run across configured feeds. | Zero raw stdout strings; 100% structured JSON logs matching schema. |
| **TC-OBS-08** | `pipeline.py` | Ingestion seed network failure simulation. | Pipeline records seed failure, logs error stack trace, and marks run without crash. |
| **TC-OBS-09** | `App.svelte` | Force synthetic 500 on `/api/profile`. | UI displays alert with `Ref: <UUID>`; server log contains identical `correlation_id`. |

---

### 10.3 Sample Log Aggregator Query Recipes

#### Elasticsearch / Kibana (KQL)
```kql
# Find all errors associated with a specific user reference ID
correlation_id: "e4d2a1b8-7c3f-4e92-a1b2-c3d4e5f6a7b8"

# Monitor OpenRouter rate-limit pressure
service: "jevscout-api" AND event: "llm.decision.completed" AND llm.rate_limit_remaining < 5

# Locate slow API routes (> 500ms)
event: "http.request.completed" AND duration_ms > 500
```

#### Grafana Loki (LogQL)
```logql
# Stream all worker failures with stack traces
{service="jevscout-worker"} | json | event =~ "worker\\..*\\.failed"

# Compute 95th percentile LLM decision latency over 5m windows
quantile_over_time(0.95, {service="jevscout-api"} | json | event = "llm.decision.completed" | unwrap duration_ms [5m])
```

#### AWS CloudWatch Insights
```sql
fields @timestamp, correlation_id, http.method, http.route, duration_ms, error.message
| filter level = 'ERROR'
| sort @timestamp desc
| limit 100
```

---

## 11. Sign-off & Architecture Approval

This technical specification establishes a complete observability framework for JevScout. It eradicates silent exception swallowing, secures sensitive credentials and candidate PII, provides comprehensive LLM financial and rate-limit tracking, and unifies request correlation across the full client-server lifecycle.

**Next Immediate Step:** Execute Phase 1 implementation by creating `backend/src/jevscout/core/observability.py`.
