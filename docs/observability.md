# Observability

> What gets logged, where, and how to read it.

---

## Two Streams

The plugin emits two complementary streams:

1. **Structured logs (stderr).** Operational events — "scan started", "manifest read failed", "render completed". Comes out of `structlog` configured in `config/logging.py`. Every helper script uses it.
2. **Audit log (`audit.jsonl`).** Run-specific events written to disk under `<output>/.tech-scout/<run-id>/audit.jsonl`. Append-only. The ground truth for "what happened during this run".

---

## Structured Logs (Stderr)

Format defaults to JSON. Set `TECH_SCOUT_LOG_FORMAT=console` for a colored human-readable form during development.

Example JSON line:

```json
{
  "event": "codebase_scan_started",
  "level": "INFO",
  "logger": "tech_scout.codebase.scanner",
  "timestamp": "2026-04-29T10:30:15+00:00",
  "run_id": "2026-04-29-abc123",
  "root": "/path/to/your-codebase"
}
```

Fields:

- `event` — snake_case event name (the *what*).
- `level` — `DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL`.
- `logger` — module path (helpful for filtering).
- `timestamp` — ISO 8601 UTC.
- `run_id` — bound via `correlation.bind_run_id()` at the top of each helper.
- Other keys — event-specific context (path, count, error message, …).

Filtering examples (jq):

```bash
# Only errors
jq 'select(.level == "ERROR")' < stderr.log

# Only events for a specific run
jq 'select(.run_id == "2026-04-29-abc123")' < stderr.log

# Count by event type
jq -r '.event' < stderr.log | sort | uniq -c
```

---

## Audit Log (`audit.jsonl`)

One JSON object per line, sorted keys, UTF-8. Lives in
`<output>/.tech-scout/<run-id>/audit.jsonl`. Created by `ts_setup_run.py`,
appended by every subsequent helper.

Schema (`AuditEvent`):

```jsonc
{
  "run_id": "2026-04-29-abc123",
  "phase": "phase-2-discovery",          // or null
  "event_type": "scan_started",
  "severity": "info",                    // debug|info|warning|error|critical
  "message": "Discovery sweep started",
  "timestamp": "2026-04-29T10:30:15+00:00",
  "payload": { "sources": 10 }
}
```

Common event types you'll see across a normal run:

| event_type | Phase | When |
|------------|-------|------|
| `run_initialized` | 0 | `ts_setup_run.py` finishes |
| `codebase_scan_started` | 1 | `ts_scan_codebase.py` starts |
| `codebase_scan_completed` | 1 | …completes |
| `manifest_read_failed` | 1 | a single manifest couldn't be parsed |
| `candidates_saved` | 3 | `ts_save_candidates.py` finishes |
| `doc_rendered` | 5 | each `ts_render_doc.py` finishes |
| `package_validated` | 6 | `ts_validate_package.py` finishes |

Reading via the SDK:

```python
from pathlib import Path
from tech_scout.observability import AuditLogger
from tech_scout.domain.value_objects import RunId

logger = AuditLogger(
    Path("/c/.../.tech-scout/2026-04-29-abc123/audit.jsonl"),
    RunId(value="2026-04-29-abc123"),
)
events = logger.read_all()
for e in events:
    print(e.timestamp, e.event_type, e.message)
```

Reading via shell (no SDK needed):

```bash
cat .tech-scout/2026-04-29-abc123/audit.jsonl | jq '.event_type'
```

---

## Why Not OpenTelemetry / Prometheus

The original plan called for both. Both got dropped. Reasons:

- The plugin runs **inside Claude Code**, which has its own telemetry layer.
- Adding OTel would require deploying a collector — operational complexity for a single-user local tool.
- Prometheus needs a long-running process to scrape; we have ephemeral CLI invocations.
- `audit.jsonl` covers the post-mortem use case (what happened during this run); structured logs cover real-time tailing.

If you ever need to ship telemetry to a central system, the cleanest extension point is to add an event handler to `AuditLogger.emit()` that also POSTs each event to your collector. The interface is intentionally narrow.

---

## Correlation IDs

Every log line within a single helper invocation carries `run_id`. Setting it:

```python
from tech_scout.observability import bind_run_id

bind_run_id("2026-04-29-abc123")
# … all subsequent log entries in this thread/task carry run_id
```

`bind_run_id` uses structlog's `contextvars`, so it's safe across `asyncio` and threads.

In helper scripts, the call happens early (right after `argparse`). Across helper invocations the binding doesn't carry over (each script is its own process), but that's fine — every helper takes `--run-id` as an argument.

---

## Diagnostic Tips

### "Why does this run claim 0 findings?"

Read the audit log:

```bash
jq 'select(.event_type == "scan_summary")' audit.jsonl
```

If the scanner subagent emitted a summary like "0 findings due to network timeout", you'll see it.

### "Why is this validator failing?"

```bash
jq 'select(.event_type == "package_validated") | .payload' audit.jsonl
```

The payload includes `error_count`, `warning_count`, and `missing` — usually enough to spot the issue.

### "Where did Phase 5 spend its time?"

Filter `doc_rendered` events and look at timestamps:

```bash
jq -r 'select(.event_type == "doc_rendered") | "\(.timestamp) \(.payload.filename)"' audit.jsonl
```

---

## Privacy

- The audit log records **filenames**, **counts**, and **event names**. It does **not** record document contents.
- The structured logs may include **paths** (codebase root, output folder) but never **file contents** or **secrets**.
- The package itself (00 through README.md) lives in the user's chosen output folder — treat it as you would any other document.

If you commit the package to git, note that `.tech-scout/` is gitignored by default — that includes the audit log and any `state.json` that mentions paths. Commit only the rendered package files (00 through README.md).
