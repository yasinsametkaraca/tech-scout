---
description: Verify the tech-scout environment — Python version, dependencies, paths, locale templates, and writable output root. Run before your first /tech-scout if anything's unclear.
argument-hint: ''
---

# /tech-scout-doctor — Environment health check

User's arguments: $ARGUMENTS (none expected)

## What to do

1. Run the helper:

```bash
python scripts/ts_doctor.py
```

2. Parse the JSON envelope. The `data.checks` array contains one entry per check, each with `name`, `status` (`ok`/`warning`/`error`), and `message`. The `data.locales` array lists registered locales.

3. Render the output as a markdown report:

```markdown
# tech-scout — Environment health

**Platform:** {{ platform }}
**Python:** {{ python_version }}
**Repo root:** `{{ repo_root }}`
**Default locale:** `{{ default_locale_code }}`

## Locales registered

{{ table of code | display_name | aliases | template_subdir }}

## Checks

| # | Check | Status | Message |
|---|-------|--------|---------|
| 1 | Python version | ✅ ok | Python 3.12 |
| 2 | import pydantic | ✅ ok | pydantic 2.7.4 |
| ... |

**Result:** {{ summary }}
```

For status icons:
- `ok` → ✅
- `warning` → ⚠️
- `error` → ❌

4. **Result paragraph**:
   - All ok: "Everything looks good. You can start with `/tech-scout`."
   - Warnings: "Ready to run, but address these warnings to avoid surprises later."
   - Errors: "These errors block `/tech-scout`: …" + concrete fix instructions.

## Common errors and fixes

| Error | Fix |
|-------|-----|
| `Python 3.10+ required` | Install Python 3.10 or newer |
| `import pydantic failed` | `pip install -e .[dev]` from the repo root |
| `Templates directory does not exist` | Make sure the `templates/` directory is in the repo |
| `Locale '<code>' is missing template(s)` | One of the per-locale template files is missing under `templates/<code>/`. Restore from git or your fork. |
| `Skill reference dir does not exist` | Make sure `.claude/skills/tech-scout/reference/` exists |
| `Output root does not exist` | Create the directory or pick an existing one for `--output` |

## No state changes

Read-only diagnostic. Doesn't write to disk (the helper itself only reads).
