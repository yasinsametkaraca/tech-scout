"""Unit tests for correlation helpers."""

from __future__ import annotations

import structlog

from tech_scout.observability import bind_run_id, clear_run_id, current_run_id


def setup_function() -> None:
    structlog.contextvars.clear_contextvars()


def test_bind_run_id_sets_current() -> None:
    bind_run_id("2026-04-29-abc123")
    assert current_run_id() == "2026-04-29-abc123"


def test_clear_removes_run_id() -> None:
    bind_run_id("2026-04-29-abc123")
    clear_run_id()
    assert current_run_id() is None


def test_current_run_id_default_none() -> None:
    structlog.contextvars.clear_contextvars()
    assert current_run_id() is None


def test_rebind_overwrites() -> None:
    bind_run_id("2026-04-29-abc123")
    bind_run_id("2026-04-29-def456")
    assert current_run_id() == "2026-04-29-def456"
