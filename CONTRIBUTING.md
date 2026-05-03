# Contributing to tech-scout

Thanks for taking the time to contribute! This document captures the
shape of a useful patch. If something is unclear or missing, open an
issue rather than guessing — the rules exist to make review fast.

---

## Quickstart

```bash
git clone https://github.com/yasinsametkaraca/tech-scout.git
cd tech-scout
make install-dev   # Installs runtime + dev deps + pre-commit hooks
make doctor        # Verifies your environment
make test          # 360+ tests should pass with coverage ≥85%
```

If `make doctor` reports any errors, fix them before opening a PR.

---

## Project Standards

The canonical engineering rules live in
[`docs/code-standards.md`](docs/code-standards.md). The TL;DR:

- **Mypy strict + Ruff strict** — both must pass with zero issues. Run
  `make lint` and `make typecheck`.
- **Pytest with ≥85% line coverage** on `src/tech_scout/`. Run
  `make test`.
- **300-line cap** per Python file (excluding docstrings/comments). If
  you cross it, split by responsibility.
- **`from __future__ import annotations`** at the top of every new
  Python file.
- **One public class per file**, mirroring filename and primary export.
- **No `print()` in library code.** Use the configured `structlog`
  logger from `tech_scout.config.logging.get_logger`.
- **Domain layer (`src/tech_scout/domain/`) is pure.** No I/O, no SDK
  imports, no logging side effects in constructors. The domain depends
  on nothing internal.

For the CLI envelope contract (the surface helper scripts speak to the
skill), see [`docs/cli-contract.md`](docs/cli-contract.md). Bumping
`envelope_version` requires explicit discussion in the PR.

---

## Workflow

1. **Open an issue first** for non-trivial changes so we can agree on the
   approach. For typo fixes or one-line nits, just send the PR.
2. **Branch from `main`.** Branch names follow `kebab-case` and lead with
   a short type tag: `feat/`, `fix/`, `refactor/`, `docs/`, `test/`,
   `chore/`. Example: `feat/add-yaml-locale`.
3. **Keep PRs small and focused.** One concern per PR. If you discover
   adjacent cleanup, prefer a follow-up PR.
4. **Write tests.** Every public function in `src/tech_scout/` has a
   matching unit test under `tests/unit/<same-path>/test_<file>.py`. Bug
   fixes ship with a regression test that fails on the broken code and
   passes after the fix.
5. **Run the gates locally** before pushing:

   ```bash
   make lint        # ruff
   make typecheck   # mypy strict
   make test        # pytest with coverage gate
   ```

6. **Update docs** when you change user-visible behavior — at minimum
   `CHANGELOG.md` (under `[Unreleased]`), and the relevant doc under
   `docs/`.
7. **Commit messages** follow imperative mood: "add foo", "fix bar",
   "refactor baz". No issue numbers in subject lines (PR descriptions
   carry that context).

---

## Adding a New Helper Command

1. Create the logic module: `src/tech_scout/cli/<name>.py` with a
   `main() -> dict[str, Any]` function and an `entry_point()` that
   delegates to `run_script(main)`. Mirror the existing modules for
   shape.
2. Add a thin shim: `scripts/ts_<name>.py` (3 lines, importing
   `entry_point` from the cli module).
3. Add a `[project.scripts]` entry in `pyproject.toml`:
   `ts-<name> = "tech_scout.cli.<name>:entry_point"`.
4. Add unit tests for `main()` in `tests/unit/cli/test_<name>.py` and
   integration tests for the script invocation in
   `tests/integration/test_helper_scripts.py`.
5. Document the command's payload shape in `docs/cli-contract.md`.

---

## Adding a New Locale

See [`docs/extending.md`](docs/extending.md). Adding a locale is
deliberately a small-surface change: register one `LocaleSpec` in
`src/tech_scout/locales/registry.py`, translate eight templates under
`src/tech_scout/templates/<code>/`, and run `make doctor` to verify.

---

## Reporting Bugs

Open a GitHub issue with:

1. **Reproduction.** Minimum commands or inputs that trigger the bug.
   For run-state bugs, the run-id and the contents of `audit.jsonl` (with
   any sensitive content redacted).
2. **Observed vs. expected behaviour.**
3. **Environment.** Output of `ts-doctor` (or `python scripts/ts_doctor.py`
   from a source checkout).

For security-sensitive reports, see [`SECURITY.md`](SECURITY.md) instead.

---

## Code of Conduct

This project follows the
[Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md). By
participating, you agree to abide by its terms.

---

## License

By contributing, you agree that your contributions will be licensed under
the [MIT License](LICENSE) that covers the project.
