# Claude Code Project Rules — tech-scout

This file is **mandatory reading** for any Claude Code session that operates on
this repository. It encodes engineering standards, architectural boundaries, and
common pitfalls. Do not deviate without an explicit user instruction.

---

## 1. Architecture Boundaries (DO NOT VIOLATE)

The codebase has three layers:

| Layer | Path | Allowed dependencies |
|-------|------|----------------------|
| 1. Claude Code Native | `.claude/` | Reads files, runs Bash. No Python imports. |
| 2. Python Helpers (CLI) | `scripts/` | Imports from `src/tech_scout/` only. |
| 3. Python Library | `src/tech_scout/` | Stdlib + declared deps in `pyproject.toml`. |

**Rules:**
- `src/tech_scout/domain/` is the innermost layer. It MUST NOT import from any
  other internal module. No I/O, no Pydantic Settings, no logging beyond what
  comes via constructor parameters.
- `src/tech_scout/locales/` may import from `domain/` only. It exposes
  per-locale data (filenames, prompts, labels) that the rest of the codebase
  consumes.
- `scripts/*.py` are CLI entry points. They parse `argparse`, call into
  `src/tech_scout/`, and emit JSON. They do not contain business logic.
- `.claude/skills/*.md` and `.claude/commands/*.md` are prompts, not code. They
  call helper scripts via Bash; they do not import Python. Locale-specific
  text (selection prompt, labels, summary template) is loaded at runtime via
  `ts_locale_info.py` — never hardcoded in markdown.

If you find yourself wanting to cross a boundary, stop and ask. The boundary
exists for a reason.

## 2. File Size Limit

No Python file may exceed **300 lines** (excluding docstrings and comments).
If you are about to write a 350-line file, split it. SRP is not a suggestion.

Markdown files (skills, reference docs, templates) have no hard limit, but
templates over 1000 lines should be split into includes.

## 3. SOLID, DRY, and Pragmatic Engineering

- **Single Responsibility:** one class/module/function does one thing.
- **Open/Closed:** when adding a new manifest reader, add a new file in
  `src/tech_scout/codebase/manifest_readers/` — do not edit existing readers.
  When adding a new locale, register a new `LocaleSpec` in
  `src/tech_scout/locales/registry.py` — do not edit existing locale specs.
- **Liskov:** subclasses honor the contract of their abstract base.
- **Interface Segregation:** small protocols/abstract classes, not god-objects.
- **Dependency Inversion:** depend on abstractions. The renderer depends on a
  `TemplateLoader` protocol, not directly on `jinja2.FileSystemLoader`.
- **DRY:** duplication of three or more lines triggers extraction. Two-line
  duplication is acceptable if extracting would obscure intent.

## 4. Verification Before Claims

When asked to describe a file, function, or behavior, **read the actual file in
this conversation first**. Do not infer from filename or memory. If uncertain,
say "let me check" and run Read or Grep before answering.

When fixing a bug, trace the actual code path with evidence. Do not guess at
root cause. If multiple interpretations are possible, investigate each against
the source until one is proven.

Inaccuracy is more harmful than slowness here.

## 5. Idempotency and State

- Helper scripts MUST be idempotent. Running `ts_setup_run.py` twice with the
  same arguments either succeeds (no-op) or refuses with a clear error.
- State files in `.tech-scout/<run-id>/` are append-mostly. Never silently
  overwrite. Use `--force` flags for destructive operations.
- `audit.jsonl` is append-only. Never delete or rewrite past entries.

## 6. Error Handling

- Domain exceptions (`src/tech_scout/domain/exceptions.py`) are the source of
  truth for error categories. Don't raise raw `ValueError` from helpers — wrap
  in a domain exception with context.
- Helper scripts catch domain exceptions, format a JSON error envelope, and
  exit with non-zero status. Skill/commands parse this envelope.
- No `except Exception:` without re-raising or logging the full traceback.
- No silent failures. If you swallow an error, document why in a comment.

## 7. Logging and Observability

- Use `structlog` configured in `src/tech_scout/config/logging.py`. Don't
  `print()` from library code (helpers may print JSON to stdout — that's the
  CLI contract, not logging).
- Every run has a `run_id`. It propagates through `correlation.bind_run_id()`
  so all log lines and audit entries carry it.
- Audit events go to `audit.jsonl` via `observability.audit_log.emit()`.
  One JSON object per line. Never multi-line entries.

## 8. Testing

- Every public function in `src/tech_scout/` has a unit test in `tests/unit/`
  with the same path. Aim for ≥85% line coverage.
- Helper scripts have integration tests in `tests/integration/` that use real
  filesystem fixtures from `tests/fixtures/`.
- Mocks are forbidden in integration tests. If you can't run the real thing,
  write a unit test instead.
- Test names follow `test_<function>_<scenario>_<expected>`. Example:
  `test_stack_detector_python_with_pyproject_returns_python_3_10`.
- Locale tests cover both registered locales (en, tr) where the behavior is
  locale-dependent (renderer, package writer, validator).

## 9. Type Hints (mypy strict)

- All functions have type hints on parameters and return.
- No `Any` unless commented why (e.g., parsing untrusted JSON).
- Pydantic models for all structured data crossing module boundaries.
- `from __future__ import annotations` at top of every Python file.

## 10. Naming

- Functions and variables: `snake_case`, descriptive. `parse_pyproject_toml`
  not `parse`.
- Classes: `PascalCase`. `ManifestReader` not `manifest_reader`.
- Constants: `UPPER_SNAKE_CASE`.
- Private: `_leading_underscore` for internal-only helpers.
- Filenames mirror their primary export. `stack_detector.py` exports
  `StackDetector` and `detect_stack()`.

## 11. Comments

Default to **no comments**. Code should be self-explanatory through naming.
Only comment when the *why* is non-obvious:
- A workaround for a specific bug (link the issue).
- A subtle invariant that would surprise a future reader.
- A choice that was deliberate but counter-intuitive.

Never:
- Restate what the code does.
- Mention current task, fix, or PR (that belongs in commit messages).
- Add multi-paragraph docstrings unless the function has complex contracts.

## 12. No External Prompt File

There is **no separate prompt template file** for this plugin. All
content rules and orchestration live inside the repo:

- `.claude/skills/tech-scout/SKILL.md` — orchestration mechanics
- `.claude/skills/tech-scout/reference/phase-N-*.md` — per-phase playbooks
- `.claude/agents/*.md` — discovery and analysis subagent rules
- `src/tech_scout/locales/*.py` — per-language strings (selection
  prompt, labels, summary template)
- `templates/<locale>/*.md.j2` — output structure

Per-run inputs (`--company`, `--codebase`, `--website`, `--focus`,
`--language`, etc.) come from CLI flags or, when missing, from
`AskUserQuestion` at the start of the run. Do not reintroduce a
`--prompt PATH` flag, a `TECH_SCOUT_DEFAULT_PROMPT_PATH` env var, or any
external prompt file without an explicit user instruction; the design
deliberately keeps content alongside code so there is one source of
truth.

When customizing workflow behavior, edit the appropriate layer (skill,
reference doc, agent definition, locale spec, template) — see
`docs/customization.md`.

## 13. Locale Layer

- All language-dependent text (filenames, validator keywords, Stage-A
  selection prompt, candidate-display labels, final summary template) lives
  in `src/tech_scout/locales/`. Adding a locale = registering one
  `LocaleSpec`.
- Helper scripts and library code never compare against literal locale text
  (e.g., "yüksek" or "high"). They look the value up via the active locale
  spec.
- Identifiers crossing module boundaries are canonical English (e.g.,
  `Finding.initial_fit ∈ {"high","medium","low"}`,
  `risks[].level ∈ {"Low","Medium","High"}`). Locales translate these only
  at the display layer.

## 14. Safety When Operating This Repo

- Do not `git push --force`, `git reset --hard`, or `rm -rf` without explicit
  user authorization.
- Do not commit `.env`, secrets, or anything in `.tech-scout/` (they're
  gitignored — verify before committing).
- Do not skip pre-commit hooks (`--no-verify`) without user authorization.

## 15. Pull Request Standard

When making changes:
1. Run `make lint` (ruff) — zero issues.
2. Run `make typecheck` (mypy strict) — zero errors.
3. Run `make test` — all green, coverage ≥85%.
4. Update `docs/` if the change is user-visible.
5. Update tests for any non-trivial change.

A PR that breaks any of the above is incomplete.

## 16. When In Doubt

Read `docs/code-standards.md` for the canonical answer. If still unclear, ask.
Don't guess.
