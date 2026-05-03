"""Unit tests for ``ts-audit-show``."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from tech_scout.cli.audit_show import (
    _coerce_timestamp,
    _filter_events,
    _format_preview,
    _parse_severities,
    _parse_since,
    _serialize_event,
    main,
)
from tech_scout.domain.exceptions import StateStoreError
from tech_scout.observability import AuditLogger
from tech_scout.observability.audit_log import AuditEvent
from tech_scout.state import AUDIT_FILENAME, StateStore

_RUN_ID = "2026-04-29-abc12345"


def _seed_audit(tmp_path: Path) -> tuple[Path, str]:
    """Build a state dir with a populated audit log; return (output, run_id)."""
    output = tmp_path / "out"
    store = StateStore(output, _RUN_ID)
    store.initialize()
    audit_path = store.state_dir / AUDIT_FILENAME
    logger = AuditLogger(audit_path, _RUN_ID)
    logger.emit("run_initialized", phase="phase-0-preparation", payload={"depth": "standard"})
    logger.emit("scan_started", phase="phase-2-discovery", payload={"sources": 10})
    logger.emit(
        "scan_warning",
        phase="phase-2-discovery",
        severity="warning",
        message="One source unreachable",
    )
    logger.emit(
        "package_validated",
        phase="phase-6-quality-check",
        severity="error",
        message="Three documents short",
    )
    return output, _RUN_ID


class TestParseSeverities:
    def test_none_returns_none(self) -> None:
        assert _parse_severities(None) is None

    def test_single_severity(self) -> None:
        assert _parse_severities("error") == {"error"}

    def test_multiple_severities(self) -> None:
        assert _parse_severities("warning, error") == {"warning", "error"}

    def test_unknown_severity_rejected(self) -> None:
        with pytest.raises(StateStoreError, match="Unknown severity"):
            _parse_severities("warning,bogus")

    def test_empty_segments_ignored(self) -> None:
        assert _parse_severities(",info,") == {"info"}


class TestParseSince:
    def test_none_returns_none(self) -> None:
        assert _parse_since(None) is None

    def test_z_suffix(self) -> None:
        out = _parse_since("2026-04-29T10:00:00Z")
        assert out is not None
        assert out.tzinfo is not None

    def test_invalid_raises(self) -> None:
        with pytest.raises(StateStoreError, match="not a valid ISO-8601"):
            _parse_since("yesterday")


class TestCoerceTimestamp:
    def test_naive_becomes_utc(self) -> None:
        naive = datetime(2026, 4, 29, 10, 0, 0)
        out = _coerce_timestamp(naive)
        assert out.tzinfo is not None

    def test_aware_passes_through(self) -> None:
        aware = datetime(2026, 4, 29, 10, 0, 0, tzinfo=timezone.utc)
        out = _coerce_timestamp(aware)
        assert out is aware


class TestFilterEvents:
    def _make(self, severity: str, ts: datetime) -> AuditEvent:
        return AuditEvent(
            run_id=_RUN_ID,
            event_type="x",
            severity=severity,
            timestamp=ts,
        )

    def test_filter_by_severity(self) -> None:
        now = datetime(2026, 4, 29, 10, 0, tzinfo=timezone.utc)
        events = [
            self._make("info", now),
            self._make("warning", now),
            self._make("error", now),
        ]
        out = list(_filter_events(events, severities={"warning", "error"}, since=None))
        assert len(out) == 2
        assert {e.severity for e in out} == {"warning", "error"}

    def test_filter_by_since(self) -> None:
        old = datetime(2026, 4, 29, 9, 0, tzinfo=timezone.utc)
        new = datetime(2026, 4, 29, 11, 0, tzinfo=timezone.utc)
        events = [self._make("info", old), self._make("info", new)]
        cutoff = datetime(2026, 4, 29, 10, 0, tzinfo=timezone.utc)
        out = list(_filter_events(events, severities=None, since=cutoff))
        assert len(out) == 1
        assert out[0].timestamp == new


class TestSerializeEvent:
    def test_round_trips_all_fields(self) -> None:
        ts = datetime(2026, 4, 29, 10, 0, tzinfo=timezone.utc)
        event = AuditEvent(
            run_id=_RUN_ID,
            phase="phase-2-discovery",
            event_type="scan_started",
            severity="info",
            message="hi",
            timestamp=ts,
            payload={"sources": 5},
        )
        out = _serialize_event(event)
        assert out["run_id"] == _RUN_ID
        assert out["phase"] == "phase-2-discovery"
        assert out["event_type"] == "scan_started"
        assert out["severity"] == "info"
        assert out["payload"] == {"sources": 5}
        assert "T" in out["timestamp"]


class TestFormatPreview:
    def test_empty_returns_placeholder(self) -> None:
        assert _format_preview([]) == "(no events)"

    def test_renders_table_header_and_rows(self) -> None:
        ts = datetime(2026, 4, 29, 10, 0, tzinfo=timezone.utc)
        events = [
            AuditEvent(
                run_id=_RUN_ID,
                phase="phase-2-discovery",
                event_type="scan_started",
                severity="info",
                message="A short message",
                timestamp=ts,
            ),
        ]
        out = _format_preview(events)
        assert "TIMESTAMP" in out
        assert "scan_started" in out
        assert "A short message" in out


class TestMain:
    def test_returns_envelope_payload(self, tmp_path: Path) -> None:
        output, run_id = _seed_audit(tmp_path)
        with patch(
            "sys.argv",
            ["ts-audit-show", "--run-id", run_id, "--output-folder", str(output)],
        ):
            body = main()
        assert body["run_id"] == run_id
        assert body["event_count_total"] == 4
        assert body["event_count_filtered"] == 4
        assert body["event_count_returned"] == 4
        assert "preview" in body
        assert "TIMESTAMP" in body["preview"]
        assert body["by_severity"]["error"] == 1

    def test_severity_filter_narrows_results(self, tmp_path: Path) -> None:
        output, run_id = _seed_audit(tmp_path)
        with patch(
            "sys.argv",
            [
                "ts-audit-show",
                "--run-id",
                run_id,
                "--output-folder",
                str(output),
                "--severity",
                "error,warning",
            ],
        ):
            body = main()
        assert body["event_count_filtered"] == 2
        assert set(body["by_severity"].keys()) == {"warning", "error"}

    def test_since_filter_skips_old_events(self, tmp_path: Path) -> None:
        output, run_id = _seed_audit(tmp_path)
        # All events are 'now-ish'; future cutoff filters everything out.
        future = (datetime.now(tz=timezone.utc) + timedelta(hours=1)).isoformat()
        with patch(
            "sys.argv",
            [
                "ts-audit-show",
                "--run-id",
                run_id,
                "--output-folder",
                str(output),
                "--since",
                future,
            ],
        ):
            body = main()
        assert body["event_count_filtered"] == 0

    def test_json_flag_drops_preview(self, tmp_path: Path) -> None:
        output, run_id = _seed_audit(tmp_path)
        with patch(
            "sys.argv",
            [
                "ts-audit-show",
                "--run-id",
                run_id,
                "--output-folder",
                str(output),
                "--json",
            ],
        ):
            body = main()
        assert "preview" not in body
        assert body["event_count_returned"] == 4

    def test_limit_truncates(self, tmp_path: Path) -> None:
        output, run_id = _seed_audit(tmp_path)
        with patch(
            "sys.argv",
            [
                "ts-audit-show",
                "--run-id",
                run_id,
                "--output-folder",
                str(output),
                "--limit",
                "2",
            ],
        ):
            body = main()
        assert body["event_count_returned"] == 2

    def test_limit_zero_means_no_limit(self, tmp_path: Path) -> None:
        output, run_id = _seed_audit(tmp_path)
        with patch(
            "sys.argv",
            [
                "ts-audit-show",
                "--run-id",
                run_id,
                "--output-folder",
                str(output),
                "--limit",
                "0",
            ],
        ):
            body = main()
        assert body["event_count_returned"] == 4

    def test_missing_audit_file_raises_state_error(self, tmp_path: Path) -> None:
        with (
            patch(
                "sys.argv",
                [
                    "ts-audit-show",
                    "--run-id",
                    _RUN_ID,
                    "--output-folder",
                    str(tmp_path / "nope"),
                ],
            ),
            pytest.raises(StateStoreError, match="No audit log"),
        ):
            main()
