# Changelog

All notable changes to **tech-scout** are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and
this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Console-script entry points** — `ts-doctor`, `ts-locale-info`,
  `ts-scan-codebase`, `ts-list-history`, `ts-setup-run`, `ts-save-candidates`,
  `ts-load-candidates`, `ts-render-doc`, and `ts-validate-package` are now
  installed by `pip install tech-scout`. The legacy `python scripts/ts_*.py`
  invocations remain as thin shims for source-checkout use.
- **Atomic state writes** (`tech_scout.utils.atomic_io.atomic_write_text`,
  `atomic_append_line`, `replace_directory_atomically`). All persisted state
  files are now written through write-temp-then-rename so a crash mid-write
  cannot corrupt them.
- **Cross-platform file lock** (`tech_scout.utils.file_lock.FileLock`) wrapping
  `msvcrt.locking` on Windows and `fcntl.flock` on POSIX. Used by `AuditLogger`
  to serialize appends from concurrent analyzer subagents.
- **Schema versioning + migration framework**
  (`tech_scout.state.migrations`). Every persisted Pydantic model now carries
  a `schema_version` field and the store runs payloads through the migration
  chain on read so old runs remain resumable across upgrades.
- **Stable error-code registry** (`tech_scout.domain.error_codes`). Every
  `TechScoutError` subclass declares a stable `error_code: ClassVar[str]`.
  Helper-script JSON envelopes now include `error_code` so callers can switch
  on a stable string instead of the Python class name. See
  `docs/cli-contract.md` for the contract.
- **Versioned CLI envelope** — every helper-script JSON envelope now carries
  `envelope_version: 1`. The contract is documented in `docs/cli-contract.md`.
- **Bundled templates as package data** — Jinja2 templates moved from
  `templates/` to `src/tech_scout/templates/` and are discovered via
  `importlib.resources` so `pip install`-ed wheels work out of the box.
- **Comprehensive doctor checks** — `ts-doctor` now exercises actual
  writability with a tempfile probe, checks free disk space, smoke-renders
  every locale's templates, exercises the cross-process audit lock, and
  round-trips the slug pipeline against known Turkish inputs. Output is
  grouped by category (`runtime`, `paths`, `packaging`, `locales`, `output`,
  `smoke`).
- **TOML compat shim** (`tech_scout.utils.toml_compat`) consolidating the
  `tomllib`/`tomli` import logic in one place.
- **OSS hygiene docs** — `CHANGELOG.md`, `CONTRIBUTING.md`, `SECURITY.md`,
  `CODE_OF_CONDUCT.md`.

### Changed

- **Field validators → model validators.** `Settings._max_geq_min` and
  `TimeWindow._end_after_start` switched from `field_validator(info=...)`
  to `model_validator(mode="after")` for Pydantic v3 readiness.
- **Helper-script DRY.** Every script under `scripts/` is now a thin shim
  delegating to a `tech_scout.cli.<name>` module. The actual logic lives
  in the package; the shims handle source-checkout `sys.path`
  bootstrapping. Removed the duplicated try/except blocks at the bottom
  of each script.
- **`AuditLogger.read_all()`** now returns `list(iter_events())`. New
  `iter_events()` method streams events one at a time for memory
  efficiency on long-running runs.
- **`pyproject.toml`** — sdist now includes the new docs (`CHANGELOG`,
  `CONTRIBUTING`, `SECURITY`, `CODE_OF_CONDUCT`). The standalone
  `templates/` entry was removed because templates now ship as package
  data.

### Fixed

- **`FileLock` cleanup on timeout.** A race in the original draft caused
  the file descriptor to be closed twice when the timeout fired,
  producing `OSError: Bad file descriptor`. Restructured around an
  `acquired` flag and a `finally` block.

### Removed

- **`scripts/_common.py`** — superseded by `tech_scout.cli._common`.

## [0.1.0] — 2026-04-30

### Added

- Initial public release of tech-scout — Claude Code-native plugin for the
  weekly tech-research workflow.
- Three-layer architecture: `.claude/` orchestration, `scripts/` CLI helpers,
  `src/tech_scout/` Python library.
- Two registered locales: English (default) and Turkish.
- Eight document slots per package: executive summary, detailed analysis,
  presentation, quick reference, diagrams, slack summary, sources, README.
- Helper scripts: `ts_doctor`, `ts_locale_info`, `ts_scan_codebase`,
  `ts_list_history`, `ts_setup_run`, `ts_save_candidates`,
  `ts_load_candidates`, `ts_render_doc`, `ts_validate_package`.
- Manifest readers for Python, Node, Rust, Go, Java/JVM, .NET.
- Pydantic v2 models for all structured data, mypy strict, ruff, 248 tests.

[Unreleased]: https://github.com/yasinsametkaraca/tech-scout/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/yasinsametkaraca/tech-scout/releases/tag/v0.1.0
