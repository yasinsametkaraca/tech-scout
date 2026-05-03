# Helper-script CLI contract

Every helper script under `scripts/` (and every `ts-*` console entry
point) speaks the same JSON envelope on stdout. The Claude Code skill —
and any other automation — parses this envelope and reacts to the
`status` and `error_code` fields. **The shape and the error codes are a
versioned contract**; we will not change them in backwards-incompatible
ways without bumping `envelope_version`.

If you build tooling on top of these helpers, dispatch on `error_code`,
not on `error_type` (which is a Python class name and may be refactored).

---

## Versioning

Every envelope carries a top-level `envelope_version: int`. The current
version is **1**. A version bump means the shape changed in a way old
clients cannot parse safely; minor additions (new optional `data` keys,
new error codes) do **not** require a bump.

---

## Success envelope

```json
{
  "envelope_version": 1,
  "status": "ok",
  "data": {
    "...": "script-specific payload"
  }
}
```

* Exit code: `0`.
* `data` is always a JSON object (never a list, string, or null).
* The shape of `data` is documented in each script's `--help` output and
  in the table below.

---

## Error envelope

```json
{
  "envelope_version": 1,
  "status": "error",
  "data": {
    "error_code": "STABLE_STRING",
    "error_type": "PythonClassName",
    "message": "Human-readable message",
    "context": {
      "...": "structured key/value details"
    }
  }
}
```

* Exit code: `1` for domain errors, `2` for unexpected exceptions, `130`
  for `Ctrl+C` (SIGINT).
* `error_code` is the **stable** identifier — switch on this in your
  client code.
* `error_type` is a Python class name kept for debugging only; do not
  rely on it.
* `context` is a JSON object whose keys depend on the error code; for
  example, `STATE_STORE_ERROR` carries `path` and `filename`,
  `PACKAGE_VALIDATION_FAILED` carries `documents_missing`.

### Stable error codes

These are exhaustive — every helper script exit goes through one of these.

| Error code | Raised when | Typical exit code |
|------------|-------------|-------------------|
| `INTERNAL_ERROR` | Unexpected Python exception (programming error) | `2` |
| `USER_INTERRUPTED` | Process killed by `Ctrl+C` (SIGINT) | `130` |
| `CONFIGURATION_INVALID` | Settings or environment misconfigured | `1` |
| `LOCALE_NOT_FOUND` | Requested locale code or alias not registered | `1` |
| `CODEBASE_SCAN_FAILED` | Codebase scanner could not read or parse the input | `1` |
| `HISTORY_LOOKUP_FAILED` | Prior-runs lookup failed | `1` |
| `STATE_STORE_ERROR` | State file read/write/parse failed | `1` |
| `TEMPLATE_RENDER_FAILED` | Jinja2 render failed (missing variable, missing template) | `1` |
| `PACKAGE_VALIDATION_FAILED` | Phase 6 found errors or missing documents | `1` |

Adding a new code: edit `src/tech_scout/domain/error_codes.py`, attach
it to a new or existing exception subclass via `error_code: ClassVar[str]`,
and document it here. The `tests/unit/domain/test_error_codes.py` module
will catch any drift between the registry and the `ALL_CODES` set.

---

## `--help` is special

`--help` and `-h` are handled by `argparse` and print the human-readable
usage to stdout. They do **not** emit a JSON envelope. Tooling that wraps
helpers should not pass these flags to the subprocess.

---

## Per-script payload reference

| Script | Console entry | `data` shape (success) |
|--------|---------------|------------------------|
| `ts_doctor.py` | `ts-doctor` | `{platform, python, repo_root, settings, locales, checks, error_count, warning_count, passed}` |
| `ts_locale_info.py` | `ts-locale-info` | `{default_code, spec}` or `{locales, default_code}` (with `--list`) |
| `ts_scan_codebase.py` | `ts-scan-codebase` | `{root_path, profile, summary}` |
| `ts_list_history.py` | `ts-list-history` | `{root, entries, total, returned}` |
| `ts_setup_run.py` | `ts-setup-run` | `{run_id, state_dir, state_file, audit_file, output_folder, language, slack_language, locale_code, slack_locale_code, reused}` |
| `ts_save_candidates.py` | `ts-save-candidates` | `{run_id, saved_path, candidate_count, candidate_ids}` |
| `ts_load_candidates.py` | `ts-load-candidates` | `{run_id, candidates, candidate_count, candidate_ids}` |
| `ts_render_doc.py` | `ts-render-doc` | `{slot, filename, locale_code, written_path, templates_root}` |
| `ts_validate_package.py` | `ts-validate-package` | `{package_path, locale_code, slack_locale_code, passed, error_count, warning_count, documents_present, documents_missing, issues}` |
| `ts_audit_show.py` | `ts-audit-show` | `{run_id, output_folder, audit_file, event_count, by_phase, by_severity, events}` |

---

## Backwards compatibility

For tooling consumers, this contract is the agreement:

1. **Don't switch on `error_type`** — it is a Python class name and may
   be renamed without notice.
2. **Don't dispatch on `message`** — it is a human-readable string and
   wording may change.
3. **`error_code` and the `data` shape are the contract**. They will not
   change in incompatible ways under the same `envelope_version`.
4. **Future fields may be added** to either `data` or `context`. Tooling
   should ignore unknown keys, not error on them.
