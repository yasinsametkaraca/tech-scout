---
description: Resume a tech-scout run at Stage B (deep analysis + package) for a previously-completed Stage A. Use this when you have a run-id and want to specify selection out-of-band (e.g., from another session).
argument-hint: '<run-id> <F-IDs comma-separated> [--depth light|standard|deep] [--output PATH]'
---

# /tech-scout-deep — Stage B with explicit selection

You're resuming a run that already completed Stage A. The user provides:

- **run-id** — e.g., `2026-04-29-abc123`
- **F-IDs** — one or more, comma-separated, e.g., `F003` or `F001,F005`
- optional **--depth** override
- optional **--output** if the run state isn't in the default location

User's arguments: $ARGUMENTS

## What to do

1. Parse the run-id and F-IDs from the arguments. If either is missing, ask the user via `AskUserQuestion`.
2. Read the skill at `.claude/skills/tech-scout/SKILL.md` and **start at Step 7 (parse selection)**.
3. Load the saved candidates by calling:
   ```bash
   python scripts/ts_load_candidates.py --run-id <id> --output-folder <output>
   ```
4. Validate that each user-supplied F-ID exists in the loaded candidates. If any is missing, list the available IDs and ask the user to pick again.
5. Read the run's locale from `state.json.request.language`, then call:
   ```bash
   python scripts/ts_locale_info.py --code <language>
   ```
   to load the locale spec for Stage B (selection prompt, labels, final summary template).
6. Continue with Stage B (Phases 4-6) per the skill, passing `--locale-code` and `--slack-locale-code` to `ts_render_doc.py` and `ts_validate_package.py`.

## Hard rules

- Don't run Phase 2 or 3 again. The candidates are already saved.
- If multiple F-IDs are passed, spawn `tech-scout-analyzer` subagents in parallel.
- After Phase 6 passes, render the locale's `final_summary_template` with the package path and slack snippet.

## On error

- Run-id not found in any output folder → ask user for the correct path or run-id.
- F-ID not in saved candidates → show available IDs.
- Analysis subagent fails twice → write partial package, tell user.
