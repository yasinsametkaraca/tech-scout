"""Append-only JSONL audit log for a research run.

Every significant event during a run is recorded in
``<output-folder>/.tech-scout/<run-id>/audit.jsonl``. The file is the
ground truth for "what happened during this run" and is essential for
debugging when a run fails.

Format: one JSON object per line, sorted keys, no trailing newline
trickery, UTF-8.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from tech_scout.config.logging import get_logger
from tech_scout.domain.value_objects import RunId

log = get_logger(__name__)


class AuditEvent(BaseModel):
    """A single audit log entry."""

    model_config = ConfigDict(frozen=True)

    run_id: str
    phase: str | None = None
    event_type: str = Field(..., min_length=1, max_length=100)
    severity: str = Field(default="info", pattern=r"^(debug|info|warning|error|critical)$")
    message: str = Field(default="", max_length=2000)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    payload: dict[str, Any] = Field(default_factory=dict)

    def to_jsonl(self) -> str:
        return self.model_dump_json(exclude_none=False)


class AuditLogger:
    """Thread-safe append-only writer for a single run's audit file.

    Multiple helper scripts may write to the same audit file in sequence
    (e.g., ``ts_setup_run.py`` then ``ts_save_candidates.py``). Within a
    single process the lock ensures partial writes don't interleave.
    Across processes we rely on append-mode atomicity for short writes.
    """

    def __init__(self, path: Path, run_id: RunId | str) -> None:
        self._path = path
        self._run_id = run_id if isinstance(run_id, RunId) else RunId(value=str(run_id))
        self._lock = Lock()

    @property
    def path(self) -> Path:
        return self._path

    def emit(
        self,
        event_type: str,
        *,
        message: str = "",
        severity: str = "info",
        phase: str | None = None,
        payload: Mapping[str, Any] | None = None,
    ) -> AuditEvent:
        event = AuditEvent(
            run_id=str(self._run_id),
            phase=phase,
            event_type=event_type,
            severity=severity,
            message=message,
            payload=dict(payload) if payload else {},
        )
        self._write(event)
        return event

    def emit_event(self, event: AuditEvent) -> None:
        if event.run_id != str(self._run_id):
            log.warning(
                "audit_run_id_mismatch",
                expected=str(self._run_id),
                got=event.run_id,
            )
        self._write(event)

    def read_all(self) -> list[AuditEvent]:
        if not self._path.is_file():
            return []
        events: list[AuditEvent] = []
        try:
            text = self._path.read_text(encoding="utf-8")
        except OSError as exc:
            log.warning("audit_read_failed", path=str(self._path), error=str(exc))
            return events
        for raw in text.splitlines():
            stripped = raw.strip()
            if not stripped:
                continue
            try:
                data = json.loads(stripped)
                events.append(AuditEvent.model_validate(data))
            except (json.JSONDecodeError, ValueError) as exc:
                log.warning(
                    "audit_line_skipped",
                    path=str(self._path),
                    error=str(exc),
                )
                continue
        return events

    def _write(self, event: AuditEvent) -> None:
        line = event.to_jsonl() + "\n"
        with self._lock:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            try:
                with self._path.open("a", encoding="utf-8") as fh:
                    fh.write(line)
            except OSError as exc:
                log.error(
                    "audit_write_failed",
                    path=str(self._path),
                    error=str(exc),
                    event_type=event.event_type,
                )
