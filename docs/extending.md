# Extending tech-scout

> How to add new capabilities without breaking existing ones.

---

## Adding a New Manifest Reader

For a new ecosystem (e.g., Ruby/Bundler):

1. **Create the file:** `src/tech_scout/codebase/manifest_readers/ruby.py`
2. **Subclass `ManifestReader`** with `ecosystem`, `language`, `claims()`, `read()`.
3. **Register it** in `manifest_readers/__init__.py`'s `DEFAULT_READERS` tuple.
4. **Add a fixture** under `tests/fixtures/sample_codebases/ruby_app/Gemfile`.
5. **Write tests** in `tests/unit/codebase/test_manifest_readers.py`.
6. **(Optional)** Add a classifier dict for common Ruby gems to map them to `StackKind`.

No other code needs to change. The scanner walks files and dispatches to whichever reader claims them.

### Worked example

```python
# src/tech_scout/codebase/manifest_readers/ruby.py
from __future__ import annotations

import re
from pathlib import Path

from tech_scout.codebase.manifest_readers._base import (
    ManifestDependency,
    ManifestReader,
    ManifestReadResult,
)
from tech_scout.domain.enums import StackKind
from tech_scout.domain.exceptions import CodebaseScanError


_FILENAMES = {"Gemfile"}
_GEM_LINE = re.compile(r"^\s*gem\s+['\"]([\w\-]+)['\"](?:\s*,\s*['\"]([^'\"]+)['\"])?")


class RubyManifestReader(ManifestReader):
    @property
    def ecosystem(self) -> str:
        return "ruby"

    @property
    def language(self) -> str:
        return "Ruby"

    def claims(self, path: Path) -> bool:
        return path.is_file() and path.name in _FILENAMES

    def read(self, path: Path) -> ManifestReadResult:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            return ManifestReadResult(
                manifest_path=path,
                ecosystem="ruby",
                language="Ruby",
                raw_metadata={"parse_error": str(exc)},
            )

        deps: list[ManifestDependency] = []
        for line in text.splitlines():
            match = _GEM_LINE.match(line)
            if match:
                name, version = match.groups()
                deps.append(
                    ManifestDependency(
                        name=name,
                        version=version,
                        kind=_classify_ruby(name),
                    )
                )

        return ManifestReadResult(
            manifest_path=path,
            ecosystem="ruby",
            language="Ruby",
            dependencies=tuple(deps),
        )


_CLASSIFIERS = {
    "rails": StackKind.FRONTEND,
    "sinatra": StackKind.FRONTEND,
    "pg": StackKind.DATABASE,
    "redis": StackKind.QUEUE,
}


def _classify_ruby(gem: str) -> StackKind:
    return _CLASSIFIERS.get(gem.lower(), StackKind.OTHER)
```

```python
# src/tech_scout/codebase/manifest_readers/__init__.py
from tech_scout.codebase.manifest_readers.ruby import RubyManifestReader

DEFAULT_READERS = (
    PythonManifestReader,
    NodeManifestReader,
    GoManifestReader,
    RustManifestReader,
    JavaManifestReader,
    DotNetManifestReader,
    RubyManifestReader,  # <-- add here
)
```

---

## Adding a New Source to the Discovery Catalog

Edit `.claude/skills/tech-scout/reference/sources-catalog.md`. Add the source to the appropriate Tier table. The scanner reads this file each run, so no code changes are needed.

If the source has unusual access patterns (e.g., a paginated API), you may want to document the access pattern in the Tier 5 section so the scanner subagent uses it correctly.

---

## Adding a New Output Document

Suppose you want a 9th document, a "letter to the team" (slot key
`team_letter`).

1. **Add the slot:** `src/tech_scout/domain/enums.py` → add
   `TEAM_LETTER = "team_letter"` to `OutputDocSlot` and to the `in_order()`
   list (canonical render order).
2. **Add a `LocaleDocumentSpec` for every registered locale** in
   `src/tech_scout/locales/en.py`, `tr.py`, etc. — supply the slot, the
   filename, the template filename, the min-word count, and any
   `required_section_keywords` for the validator.
3. **Create the template per locale:** `templates/<code>/<filename>.j2`.
4. **Document the context:** add a section to
   `.claude/skills/tech-scout/reference/output-templates-guide.md` listing
   the required context fields.
5. **Update the analyzer subagent**
   (`.claude/agents/tech-scout-analyzer.md`) to populate those fields in
   its output JSON.
6. **Add a render integration test** in
   `tests/integration/test_helper_scripts.py`.

The skill picks up the new slot automatically because Phase 5 iterates
`OutputDocSlot.in_order()`. The validator and writer learn about the new
filename + rules from the locale spec — no edits needed in
`output/validator.py` or `output/package_writer.py`.

---

## Adding a New Locale

Adding a locale means registering one `LocaleSpec` and providing eight
templates. No changes to library or helper code.

1. **Create `src/tech_scout/locales/<code>.py`** (e.g. `de.py` for German).
   Mirror the structure of `en.py` — it's the canonical reference. Translate
   every text field: `documents[*].required_section_keywords`,
   `selection_prompt`, `selection_examples`, `final_summary_template`,
   `candidate_display_labels`, `score_axis_labels`, `fit_label_map`.
2. **Pick a unique two-letter `code`** and a `Language` enum value. If the
   language isn't already in `Language`, add it (e.g. `GERMAN = "german"`)
   and update the `_LANGUAGE_CODES` map in
   `src/tech_scout/domain/enums.py`.
3. **Register the new instance** in `src/tech_scout/locales/registry.py`'s
   `_DEFAULT_REGISTRY`.
4. **Create `templates/<code>/`** and translate every template from
   `templates/en/`. Preserve all Jinja field names exactly — only prose
   and labels change.
5. **Update `make test`** — locale-specific tests should iterate over the
   registered locales rather than hardcode codes.
6. **Run `make doctor`** to confirm all 8 templates are present for the
   new locale.

Done. `/tech-scout --language <code>` will now route the run through the
new locale.

---

## Adding a New Slash Command

Example: `/tech-scout-archive` to package up old runs into a tarball.

1. **Create the markdown:** `.claude/commands/tech-scout-archive.md`. Frontmatter has `description` and `argument-hint`. Body describes what to do (list runs, tar them, summarize).
2. **(Optional) Add a helper script:** `scripts/ts_archive.py` if there's deterministic logic. Otherwise the slash command can just use built-in tools.
3. **Update `README.md`** to mention the new command.

No skill changes needed if the command doesn't share orchestration with `/tech-scout`.

---

## Adding a New Run-State File

Example: store user preferences as `<state_dir>/preferences.json`.

1. **Add a constant** in `src/tech_scout/state/schemas.py` (e.g., `PREFERENCES_FILENAME`).
2. **Add a Pydantic model** in `src/tech_scout/domain/models.py` for the schema.
3. **Add `read_preferences()` and `write_preferences()`** methods to `StateStore`.
4. **Use them** from helper scripts as needed.
5. **Add unit tests** for the schema + StateStore round-trip.

The validator and audit log don't need to know — they only care about specific files (`audit.jsonl`, the package files).

---

## Adding Telemetry / Metrics Export

The cleanest place to hook in telemetry is `AuditLogger`. Subclass it (or add a callback registry) so each `emit()` call also pushes to your collector:

```python
# Pseudocode
class TelemetryAuditLogger(AuditLogger):
    def __init__(self, *args, telemetry_client, **kwargs):
        super().__init__(*args, **kwargs)
        self._tel = telemetry_client

    def _write(self, event):
        super()._write(event)
        self._tel.publish(event)
```

Wire it up via dependency injection in helpers (you'd need to extend `_common.py` to allow injecting a custom logger).

---

## Adding a Different LLM Backend

Currently the plugin runs entirely on Claude Code's built-in tools. If you wanted to swap to another LLM (e.g., for cost or air-gap reasons):

- **You'd lose the slash command + skill + subagent abstraction.** Those are Claude Code primitives. So this is a bigger change than a "swap".
- A reasonable port would be: rewrite Layer 1 as a Python orchestrator that calls the new LLM directly, keep Layer 2 (helpers) and Layer 3 (lib) unchanged.

This is essentially the original plan we scrapped. It's possible, just much more code.

---

## Refactoring Guidelines

- **One change at a time.** Don't bundle "add Ruby reader" with "rename three things in domain". Smaller PRs.
- **Tests first.** When changing behavior, write the failing test first.
- **Update docs.** If you change a public surface (slash command, helper CLI, schema), update the relevant doc.
- **Run all checks.** `make lint && make typecheck && make test`. CI will block if any fail.
