"""Append-only JSONL audit log for a research run.

Every significant event during a run is recorded in
``<output-folder>/.tech-scout/<run-id>/audit.jsonl``. The file is the
ground truth for "what happened during this run" and is essential for
debugging when a run fails.

Format: one JSON object per line, sorted keys, no trailing newline
trickery, UTF-8.

Concurrency: phase 4 spawns one analyzer subagent per chosen candidate,
each running as a separate Bash process. They may all emit audit events
into the same ``audit.jsonl``. To prevent interleaved partial lines we
combine an in-process :class:`threading.Lock` with a cross-process
:class:`tech_scout.utils.file_lock.FileLock`. Together they serialize
appends from any thread in any process on the same machine.
"""

from __future__ import annotations

import json
from collections.abc import Iterator, Mapping
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from tech_scout.config.logging import get_logger
from tech_scout.domain.value_objects import RunId
from tech_scout.utils.atomic_io import atomic_append_line
from tech_scout.utils.file_lock import FileLock, FileLockTimeoutError

log = get_logger(__name__)

_LOCK_FILENAME_SUFFIX = ".lock"
_DEFAULT_LOCK_TIMEOUT_SECONDS = 10.0


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
    """Thread-safe and process-safe append-only writer for one run's audit file.

    Two layers of mutual exclusion:

    * A :class:`threading.Lock` instance serializes calls within a single
      Python process (multiple threads, async tasks).
    * A :class:`~tech_scout.utils.file_lock.FileLock` on a sibling
      ``audit.jsonl.lock`` file serializes calls *across* processes —
      essential for Phase 4, which fans out one analyzer subagent per
      chosen candidate, each running as its own process.

    Combined with :func:`tech_scout.utils.atomic_io.atomic_append_line`
    (which uses ``O_APPEND``), this guarantees that every audit line lands
    intact even under concurrent writers.
    """

    def __init__(
        self,
        path: Path,
        run_id: RunId | str,
        *,
        lock_timeout_seconds: float = _DEFAULT_LOCK_TIMEOUT_SECONDS,
    ) -> None:
        self._path = path
        self._run_id = run_id if isinstance(run_id, RunId) else RunId(value=str(run_id))
        self._lock = Lock()
        self._cross_process_lock = FileLock(
            path.with_name(path.name + _LOCK_FILENAME_SUFFIX),
            timeout_seconds=lock_timeout_seconds,
        )

    @property
    def path(self) -> Path:
        return self._path

    @property
    def lock_path(self) -> Path:
        return self._cross_process_lock.path

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

    def iter_events(self) -> Iterator[AuditEvent]:
        """Yield events one at a time — memory-friendly for large logs.

        Lines that fail to parse are skipped with a warning rather than
        aborting the iteration, so a single corrupt line cannot lose the
        rest of the file.
        """
        if not self._path.is_file():
            return
        try:
            handle = self._path.open(encoding="utf-8")
        except OSError as exc:
            log.warning("audit_read_failed", path=str(self._path), error=str(exc))
            return
        with handle as fh:
            for raw in fh:
                stripped = raw.strip()
                if not stripped:
                    continue
                try:
                    data = json.loads(stripped)
                    yield AuditEvent.model_validate(data)
                except (json.JSONDecodeError, ValueError) as exc:
                    log.warning(
                        "audit_line_skipped",
                        path=str(self._path),
                        error=str(exc),
                    )
                    continue

    def read_all(self) -> list[AuditEvent]:
        return list(self.iter_events())

    def _write(self, event: AuditEvent) -> None:
        line = event.to_jsonl() + "\n"
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            try:
                with self._cross_process_lock:
                    atomic_append_line(self._path, line)
            except FileLockTimeoutError as exc:
                log.error(
                    "audit_lock_timeout",
                    path=str(self._path),
                    lock_path=str(self._cross_process_lock.path),
                    error=str(exc),
                    event_type=event.event_type,
                )
            except OSError as exc:
                log.error(
                    "audit_write_failed",
                    path=str(self._path),
                    error=str(exc),
                    event_type=event.event_type,
                )
