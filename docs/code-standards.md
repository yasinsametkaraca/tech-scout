# Code Standards — tech-scout

This document is the canonical source for code-quality rules in this repository.
`CLAUDE.md` references it; new contributors read it; pull requests are reviewed
against it.

If a rule below conflicts with `CLAUDE.md`, the stricter interpretation wins.

---

## 1. Language Targets

| Item | Setting |
|------|---------|
| Python minimum version | **3.10** |
| `from __future__ import annotations` | Required at top of every `.py` file |
| Mypy strict mode | Required (see `pyproject.toml`) |
| Ruff lint level | Strict (see `pyproject.toml`) |

## 2. File Organization

### 2.1 Directory Layering (enforced)

```
src/tech_scout/                  Library — pure Python, importable
  domain/                        Innermost: no I/O, no SDK, no logging-as-side-effect
  config/                        Settings + structlog setup
  cli/                           Console-script entry points (ts-doctor, ts-render-doc, …)
  codebase/, history/,
  output/, state/,
  observability/, utils/         Infrastructure modules
  templates/                     Jinja2 *.md.j2 (shipped as package data)
scripts/                         Thin shims for python scripts/ts_*.py invocation
tests/                           Pytest tests, mirroring src/tech_scout/ layout
.claude/                         Claude Code plugin definition (no Python here)
docs/                            Markdown documentation
```

### 2.2 File Size

- **Python:** ≤ 300 lines per file (excluding docstrings/comments). If you cross
  this, split by responsibility (not by line count).
- **Markdown templates:** ≤ 1000 lines. Use Jinja `{% include %}` to compose.
- **Reference docs (`.claude/skills/.../reference/*.md`):** No hard limit, but
  one focused topic per file.

### 2.3 One Public Class Per File

A file like `stack_detector.py` contains a `StackDetector` class plus a single
`detect_stack()` convenience function. It does not also contain an
`HistoryRepository`. Mixed-purpose files are a code smell.

## 3. Naming

| Kind | Convention | Example |
|------|-----------|---------|
| Variable, function | `snake_case`, descriptive | `parse_pyproject_toml` |
| Class | `PascalCase` | `ManifestReader` |
| Constant | `UPPER_SNAKE_CASE` | `DEFAULT_MAX_FINDINGS` |
| Private | `_leading_underscore` | `_normalize_locale` |
| Module | `snake_case`, mirrors primary export | `stack_detector.py` |
| Type variable | `T`, `U` (single capital) or descriptive `TModel` | `T = TypeVar("T")` |
| Pydantic model | Noun phrase, `PascalCase` | `ResearchRequest` |
| Pydantic field | `snake_case` | `output_folder` |
| Enum | `PascalCase` for class, `UPPER_SNAKE_CASE` for members | `Depth.LIGHT` |

**Avoid:** abbreviations (`mngr`, `ctx`, `tmp`), single-letter names except in
short comprehensions (`for c in candidates`), Hungarian notation (`strName`).

## 4. Type Hints

### 4.1 Required

- Every function parameter is typed.
- Every function returns a typed value (`-> None` if void).
- Every class attribute (instance or class) is annotated.
- `from __future__ import annotations` is at the top of every file.

### 4.2 Forbidden Without Justification

- `Any` — comment why if used (e.g., parsing untrusted JSON).
- `# type: ignore` — comment with the reason and link to issue.
- `cast()` — prefer narrowing via `isinstance` or assertion.

### 4.3 Pydantic Over Plain Classes for Data

If a structure crosses a module boundary or is serialized, use Pydantic. Plain
`@dataclass` only for internal-only structures.

## 5. Function Design

### 5.1 Length

A function should fit on a screen (≤40 lines). If longer, extract helpers with
descriptive names.

### 5.2 Arguments

- ≤5 positional/keyword arguments. More → group into a Pydantic model.
- Keyword-only after the third argument: `def f(a, b, c, *, d, e):`.
- Boolean parameters always keyword-only: `def render(*, force: bool = False)`.

### 5.3 Single Return Point Preferred

Multiple `return` statements are OK for early-exit guards. Avoid deeply nested
returns inside loops — extract.

### 5.4 No Side Effects in Constructors

`__init__` stores; it does not call out to disk, network, or subprocess. If
expensive setup is needed, use a classmethod factory: `cls.from_path(...)`.

## 6. Error Handling

### 6.1 Domain Exceptions

`src/tech_scout/domain/exceptions.py` defines the exception hierarchy:

```python
class TechScoutError(Exception):
    """Base for all domain errors."""

class CodebaseScanError(TechScoutError): ...
class StateStoreError(TechScoutError): ...
class TemplateRenderError(TechScoutError): ...
class HistoryLookupError(TechScoutError): ...
class ValidationError(TechScoutError): ...
```

Library code raises these. Helpers catch and convert to JSON error envelopes.

### 6.2 No Bare `except`

`except:` and `except Exception:` are banned unless followed by re-raise or
explicit logging:

```python
try:
    risky()
except SpecificError as e:
    logger.warning("expected failure", error=str(e))
    raise DomainError("Could not …") from e
```

### 6.3 Raise With Context

`raise ... from e` for chained exceptions. Lose the chain only when
intentionally hiding internals.

## 7. Logging

### 7.1 structlog Only

```python
from tech_scout.config.logging import get_logger
log = get_logger(__name__)

log.info("scan_started", path=str(path), reader_count=len(readers))
```

- Event name is the **first positional argument** (snake_case).
- Context is **keyword arguments** (no f-strings inside the event name).
- Numeric values, paths, IDs go in kwargs — not in the event string.

### 7.2 No `print()` in Library Code

`src/tech_scout/` may not call `print()`. Helpers in `scripts/` may print JSON
to stdout (it's the CLI contract). Use logging for everything else.

### 7.3 Levels

| Level | When |
|-------|------|
| `debug` | Verbose tracing, off by default |
| `info` | Lifecycle events: started/completed |
| `warning` | Recoverable degradations |
| `error` | Failed operation, exception caught |
| `critical` | Process can't continue |

## 8. Imports

### 8.1 Order (ruff/isort enforces)

1. `from __future__ import annotations`
2. Standard library
3. Third-party
4. First-party (`tech_scout.*`)
5. Local relative (`.`, `..`)

### 8.2 Style

- Absolute imports preferred: `from tech_scout.domain.models import Candidate`.
- Relative only within tightly coupled subpackages: `from ._base import ManifestReader`.
- No `from x import *`.
- One symbol per import line if more than 3 symbols: split.

## 9. Testing

### 9.1 Layout

```
tests/unit/<module-path>/test_<file>.py    # Mirror src/tech_scout/<module-path>/<file>.py
tests/integration/test_<script>.py         # One per scripts/<script>.py
```

### 9.2 Test Naming

```python
def test_<unit>_<scenario>_<expected>():
    ...

# Examples
def test_stack_detector_with_pyproject_returns_python(): ...
def test_setup_run_script_idempotent_returns_same_run_id(): ...
def test_renderer_missing_variable_raises_template_render_error(): ...
```

### 9.3 Arrange-Act-Assert

```python
def test_renderer_with_valid_data_renders_template():
    # Arrange
    renderer = Renderer(loader=DictLoader({"x.j2": "Hello {{name}}"}))

    # Act
    result = renderer.render("x.j2", {"name": "Yasin"})

    # Assert
    assert result == "Hello Yasin"
```

### 9.4 Fixtures

- Shared fixtures in `tests/conftest.py`.
- Fixture names match the resource: `def sample_pyproject(tmp_path) -> Path:`.
- Prefer `tmp_path` over manual `mkdtemp`.
- Real filesystem in integration tests; mocks only in unit tests.

### 9.5 Coverage

≥85% line coverage on `src/tech_scout/`. Helpers in `scripts/` exempt
(integration tests cover them via subprocess).

## 10. Documentation

### 10.1 Docstrings

- Public classes and functions have one-paragraph docstrings.
- No multi-paragraph docstrings unless the contract is genuinely complex.
- Format: short imperative summary, optional longer description, optional
  `Args:` / `Returns:` / `Raises:` sections.

```python
def detect_stack(root: Path) -> StackProfile:
    """Detect the technology stack used at *root*.

    Walks manifest files and asks each registered reader to claim them.
    Combines reader outputs into a single profile.

    Raises:
        CodebaseScanError: if *root* is not a directory or is unreadable.
    """
```

### 10.2 Comments (Inline)

Default to **none**. Add only when the *why* is non-obvious. Prohibited:

- "// add 1 to x" (says what)
- "// fix for issue #42" (rots; goes in commit message)
- Section dividers like `# ============== END OF FUNCTION ===============`

### 10.3 Module Docstrings

Optional. If present, one short paragraph describing the module's
responsibility.

## 11. Dependency Discipline

- Every new dependency requires a one-paragraph justification in the PR
  description.
- Remove unused dependencies in the same PR that drops their last consumer.
- No experimental dependencies (alpha/beta) without a fallback plan documented.

## 12. Idempotency

CLI helpers must be idempotent:

- `ts_setup_run.py <args>`: second call with same args is a no-op (or refuses
  with clear error).
- `ts_render_doc.py`: deterministic output for same input.
- `ts_save_candidates.py`: refuses to overwrite without `--force`.

## 13. Security

- Never log secrets. If a value might be sensitive, hash or redact before
  logging.
- Validate all path inputs against directory traversal (`..`).
- Subprocess: never `shell=True` with user-controlled input.
- File writes go to `output_folder` only — never write outside it.

## 14. Performance

- Premature optimization is forbidden. Write clear code first.
- If profiling reveals a hotspot, document the profiling result in a comment
  and link the optimization PR.
- I/O and CPU work in helpers stays under 60 seconds for normal inputs. If
  longer, emit progress JSON.

## 15. Pull Request Checklist

Before merging:

- [ ] `make lint` — zero issues
- [ ] `make typecheck` — zero errors
- [ ] `make test` — all green, coverage ≥85%
- [ ] Docs updated for user-visible changes
- [ ] CHANGELOG.md entry (when one is added)
- [ ] No new TODO comments without linked issues
- [ ] No `# type: ignore` without justification comment
