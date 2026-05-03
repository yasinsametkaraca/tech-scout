"""``ts-audit-show`` — render a run's ``audit.jsonl`` for humans.

The audit log is the source of truth for "what happened during a run".
Helper scripts emit one JSONL event per significant action; this command
loads them, summarizes by phase and severity, and either prints a human
table or returns the structured data via the standard envelope so other
tooling can consume it.

Usage::

    ts-audit-show --run-id 2026-04-29-abc123 --output-folder PATH
    ts-audit-show --run-id ... --output-folder ... --since 2026-04-29T10:00:00Z
    ts-audit-show --run-id ... --output-folder ... --severity warning,error
    ts-audit-show --run-id ... --output-folder ... --json   # machine-only
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from collections.abc import Iterable
from datetime import datetime
from typing import Any, NoReturn

from tech_scout.cli._common import parse_path, run_script
from tech_scout.domain.exceptions import StateStoreError
from tech_scout.observability import AuditLogger
from tech_scout.observability.audit_log import AuditEvent
from tech_scout.state import AUDIT_FILENAME, StateStore
from tech_scout.utils.time import parse_iso_datetime

_VALID_SEVERITIES = {"debug", "info", "warning", "error", "critical"}


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ts-audit-show",
        description="Show the audit log for a research run.",
    )
    p.add_argument("--run-id", required=True)
    p.add_argument("--output-folder", type=parse_path, required=True)
    p.add_argument(
        "--since",
        default=None,
        help=(
            "ISO-8601 timestamp; only events at or after this time are shown. "
            "Both 'Z' and '+HH:MM' suffixes are accepted."
        ),
    )
    p.add_argument(
        "--severity",
        default=None,
        help=(
            "Comma-separated severities to include (debug, info, warning, "
            "error, critical). Defaults to all."
        ),
    )
    p.add_argument(
        "--limit",
        type=int,
        default=200,
        help="Maximum number of events to return (default: 200, 0 = no limit).",
    )
    p.add_argument(
        "--json",
        action="store_true",
        help=(
            "Skip the human-readable summary in `data.preview` and return only "
            "the structured event list. Useful for piping into another tool."
        ),
    )
    return p


def main() -> dict[str, Any]:
    args = _build_parser().parse_args()

    severities = _parse_severities(args.severity)
    since = _parse_since(args.since)

    store = StateStore(args.output_folder, args.run_id)
    audit_path = store.state_dir / AUDIT_FILENAME
    if not audit_path.is_file():
        raise StateStoreError(
            f"No audit log found for run {args.run_id} at {audit_path}",
            context={"run_id": args.run_id, "expected_path": str(audit_path)},
        )

    logger = AuditLogger(audit_path, args.run_id)
    raw_events: list[AuditEvent] = list(logger.iter_events())

    filtered = list(_filter_events(raw_events, severities=severities, since=since))
    limit = max(args.limit, 0)
    truncated = filtered[-limit:] if limit > 0 else filtered

    by_phase = Counter(e.phase or "(unknown)" for e in filtered)
    by_severity = Counter(e.severity for e in filtered)

    body: dict[str, Any] = {
        "run_id": args.run_id,
        "output_folder": str(args.output_folder),
        "audit_file": str(audit_path),
        "event_count_total": len(raw_events),
        "event_count_filtered": len(filtered),
        "event_count_returned": len(truncated),
        "by_phase": dict(by_phase),
        "by_severity": dict(by_severity),
        "events": [_serialize_event(e) for e in truncated],
    }
    if not args.json:
        body["preview"] = _format_preview(truncated)
    return body


def _parse_severities(raw: str | None) -> set[str] | None:
    if raw is None:
        return None
    requested = {part.strip().lower() for part in raw.split(",") if part.strip()}
    invalid = requested - _VALID_SEVERITIES
    if invalid:
        raise StateStoreError(
            f"Unknown severity values: {sorted(invalid)}. Allowed: {sorted(_VALID_SEVERITIES)}",
            context={"requested": sorted(requested)},
        )
    return requested


def _parse_since(raw: str | None) -> datetime | None:
    if raw is None:
        return None
    try:
        return parse_iso_datetime(raw)
    except ValueError as exc:
        raise StateStoreError(
            f"--since is not a valid ISO-8601 timestamp: {raw!r}",
            context={"value": raw, "error": str(exc)},
        ) from exc


def _filter_events(
    events: Iterable[AuditEvent],
    *,
    severities: set[str] | None,
    since: datetime | None,
) -> Iterable[AuditEvent]:
    for event in events:
        if severities is not None and event.severity not in severities:
            continue
        if since is not None and _coerce_timestamp(event.timestamp) < since:
            continue
        yield event


def _coerce_timestamp(value: datetime) -> datetime:
    """Strip naive timestamps onto UTC so comparisons against `--since` work."""
    if value.tzinfo is None:
        from datetime import timezone

        return value.replace(tzinfo=timezone.utc)
    return value


def _serialize_event(event: AuditEvent) -> dict[str, Any]:
    return {
        "timestamp": event.timestamp.isoformat(),
        "run_id": event.run_id,
        "phase": event.phase,
        "event_type": event.event_type,
        "severity": event.severity,
        "message": event.message,
        "payload": event.payload,
    }


def _format_preview(events: list[AuditEvent]) -> str:
    """Produce a single-string human table — the skill prints this verbatim."""
    if not events:
        return "(no events)"
    lines: list[str] = []
    lines.append(f"{'TIMESTAMP':<20}  {'PHASE':<24}  {'SEVERITY':<8}  EVENT")
    lines.append("-" * 80)
    for e in events:
        ts = e.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        phase = (e.phase or "")[:24]
        msg = e.message or e.event_type
        if len(msg) > 60:
            msg = msg[:57] + "..."
        lines.append(f"{ts:<20}  {phase:<24}  {e.severity:<8}  {e.event_type}: {msg}")
    return "\n".join(lines)


def entry_point() -> NoReturn:
    if "--help" in sys.argv or "-h" in sys.argv:
        _build_parser().print_help()
        raise SystemExit(0)
    run_script(main)


if __name__ == "__main__":  # pragma: no cover
    entry_point()
