"""Unit tests for the audit logger."""

from __future__ import annotations

import json
import multiprocessing
from pathlib import Path

from tech_scout.observability import AuditLogger


def test_emit_writes_jsonl(tmp_path: Path) -> None:
    audit_path = tmp_path / "audit.jsonl"
    logger = AuditLogger(audit_path, "2026-04-29-abc123")
    event = logger.emit(
        "scan_started",
        message="Discovery sweep started",
        phase="phase-2-discovery",
        payload={"sources": 10},
    )
    assert event.event_type == "scan_started"
    assert audit_path.is_file()
    lines = audit_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    obj = json.loads(lines[0])
    assert obj["run_id"] == "2026-04-29-abc123"
    assert obj["event_type"] == "scan_started"
    assert obj["payload"] == {"sources": 10}


def test_multiple_emits_append(tmp_path: Path) -> None:
    logger = AuditLogger(tmp_path / "audit.jsonl", "2026-04-29-abc123")
    logger.emit("e1")
    logger.emit("e2")
    logger.emit("e3")
    events = logger.read_all()
    assert [e.event_type for e in events] == ["e1", "e2", "e3"]


def test_read_all_empty_file_returns_empty(tmp_path: Path) -> None:
    logger = AuditLogger(tmp_path / "missing.jsonl", "2026-04-29-abc123")
    assert logger.read_all() == []


def test_read_all_skips_malformed_line(tmp_path: Path) -> None:
    audit_path = tmp_path / "audit.jsonl"
    audit_path.write_text(
        '{"run_id":"2026-04-29-abc123","event_type":"valid","severity":"info","message":""}\n'
        "not json\n"
        '{"run_id":"2026-04-29-abc123","event_type":"valid2","severity":"info","message":""}\n',
        encoding="utf-8",
    )
    logger = AuditLogger(audit_path, "2026-04-29-abc123")
    events = logger.read_all()
    types = {e.event_type for e in events}
    assert "valid" in types
    assert "valid2" in types


def test_severity_validation() -> None:
    import pytest

    from tech_scout.observability.audit_log import AuditEvent

    AuditEvent(run_id="2026-04-29-abc123", event_type="x", severity="info")
    AuditEvent(run_id="2026-04-29-abc123", event_type="x", severity="error")
    with pytest.raises(Exception):
        AuditEvent(run_id="2026-04-29-abc123", event_type="x", severity="bogus")


def test_iter_events_streams(tmp_path: Path) -> None:
    logger = AuditLogger(tmp_path / "audit.jsonl", "2026-04-29-abc123")
    for i in range(5):
        logger.emit(f"event_{i}", payload={"i": i})
    streamed = [e.event_type for e in logger.iter_events()]
    assert streamed == [f"event_{i}" for i in range(5)]


def test_lock_path_sibling_to_audit(tmp_path: Path) -> None:
    audit_path = tmp_path / "audit.jsonl"
    logger = AuditLogger(audit_path, "2026-04-29-abc123")
    assert logger.lock_path == tmp_path / "audit.jsonl.lock"


def _emit_n(args: tuple[str, str, int]) -> None:
    """Helper for the cross-process append test (must be picklable)."""
    audit_str, run_id, count = args
    audit_path = Path(audit_str)
    logger = AuditLogger(audit_path, run_id, lock_timeout_seconds=30.0)
    for i in range(count):
        logger.emit("multi_proc", payload={"i": i})


def test_concurrent_processes_do_not_interleave_lines(tmp_path: Path) -> None:
    audit_path = tmp_path / "audit.jsonl"
    run_id = "2026-04-29-abc123"
    proc_count = 4
    per_proc = 25
    args = [(str(audit_path), run_id, per_proc)] * proc_count
    ctx = multiprocessing.get_context("spawn")
    with ctx.Pool(proc_count) as pool:
        pool.map(_emit_n, args)
    # Every line must be parseable JSON — interleaving would corrupt some.
    text = audit_path.read_text(encoding="utf-8")
    lines = [line for line in text.splitlines() if line.strip()]
    assert len(lines) == proc_count * per_proc
    for line in lines:
        json.loads(line)
