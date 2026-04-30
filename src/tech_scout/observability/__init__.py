"""Observability primitives — audit log, correlation IDs.

Lightweight by design: a single JSONL file per run for the audit trail,
and structlog contextvars for correlation. We don't need OpenTelemetry
or Prometheus here — Claude Code provides its own telemetry, and these
helpers are short-lived per-run.
"""

from __future__ import annotations

from tech_scout.observability.audit_log import AuditEvent, AuditLogger
from tech_scout.observability.correlation import bind_run_id, clear_run_id, current_run_id

__all__ = [
    "AuditEvent",
    "AuditLogger",
    "bind_run_id",
    "clear_run_id",
    "current_run_id",
]
