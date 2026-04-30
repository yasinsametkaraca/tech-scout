---
description: Show a summary of a past research run — opens the package and prints the executive summary, slack snippet, and key references.
argument-hint: '<slug-or-folder-name> [--root PATH]'
---

# /tech-scout-show — Display a past research run

User's arguments: $ARGUMENTS

## What to do

1. Parse the slug from the first argument. It can be:
   - The bare slug: `memory-layer-ai-agents`
   - The full folder name: `2026-04-22-memory-layer-ai-agents`
2. Determine the root (default or `--root`).
3. List history to find the matching folder:
   ```bash
   python scripts/ts_list_history.py "<root>" --limit 100
   ```
4. Find the entry whose `folder_slug` matches (or whose `folder_path` ends with the supplied slug).
5. If not found, ask the user for the right slug, listing the closest matches.
6. **Detect the locale of the package** by inspecting filenames in the folder. Each registered locale has a unique set of slot filenames; match those to identify the locale. Or read `.tech-scout/<run-id>/state.json` if it exists and use its `request.language` field.
7. Once found, **read** the following files from the package folder (filenames depend on the detected locale's `documents` mapping):
   - The `executive_summary` slot file — print the entire content (it's short)
   - The `slack_summary` slot file — print the entire content
   - The `sources` slot file — print the "Primary Sources" section only (table heading varies by locale; rely on the document's first H2 after the intro)
   - The `readme` slot file — print the "Three Core Messages" and "Suggested Next Steps" sections
8. Render a clean output:

```markdown
# {{ topic title }} — Summary

**Date:** {{ date }}
**Slug:** `{{ slug }}`
**Folder:** `{{ folder_path }}`
**Language:** `{{ locale_code }}`

---

{{ contents of the executive_summary doc }}

---

## Slack-ready snippet

{{ contents of the slack_summary doc }}

---

## Primary sources

{{ section from the sources doc }}

---

## Three core messages

{{ from the readme doc }}

## Suggested next steps

{{ from the readme doc }}
```

## On error

- Slug not found → list close matches and ask.
- Some files in the package are missing → print what exists, note what's missing.
- Files unreadable → surface the OS error.
- Locale could not be detected (filenames don't match any registered locale) → prompt the user to specify which locale was used.

## No state changes

Read-only.
