---
description: Resume an interrupted research run from where it left off. Reads phase progress and continues from the last incomplete phase.
argument-hint: '<run-id> [--output PATH]'
---

# /tech-scout-resume — Continue a paused run

User's arguments: $ARGUMENTS

## What to do

1. Parse the run-id from the first argument.
2. Determine the output folder:
   - If `--output PATH` provided, use it.
   - Otherwise, search the configured default research-documentation root for any `.tech-scout/<run-id>/` directory and infer the output folder.
3. Load the run state:
   - `<output>/.tech-scout/<run-id>/state.json` — must exist
   - `<output>/.tech-scout/<run-id>/phase-progress.json` — may not exist for very fresh runs
   - `<output>/.tech-scout/<run-id>/candidates.json` — exists if Phase 3 completed
   - `<output>/.tech-scout/<run-id>/selection.json` — exists if user already picked
4. Load the locale spec by reading `state.json.request.language` and calling:
   ```bash
   python scripts/ts_locale_info.py --code <language>
   ```
5. Determine the last completed phase and the next phase to run:
   - No `candidates.json` → resume Phase 0 (re-run from the start)
   - `candidates.json` exists, no `selection.json` → re-render the candidate display, prompt user for selection (mid-Stage-A)
   - `selection.json` exists, no `analysis-*.json` files → resume Phase 4 with the saved selection
   - `analysis-*.json` files exist, package files missing → resume Phase 5 (packaging) — pass `--locale-code` and `--slack-locale-code` to `ts_render_doc.py`
   - Package files exist, validation didn't pass → resume Phase 6 — pass the same locale codes to `ts_validate_package.py`
6. Read the skill (`.claude/skills/tech-scout/SKILL.md`) and continue from the determined phase.

## What you may need to ask the user

- If `selection.json` is missing AND `candidates.json` exists, you're at the Stage A wait point. Re-print the candidate display per `reference/candidate-format.md` and use the locale's `selection_prompt` verbatim.

## On error

- Run-id not found → list known run-ids in the output root, suggest the closest one.
- State files corrupted → surface the validation error and ask whether the user wants to start fresh.
- Selection points to an F-ID that no longer exists in candidates (shouldn't happen, but…) → ask user.

## Hard rules

- Do not re-run a phase that already completed. Use the audit log if `phase-progress.json` is unclear.
- Don't auto-pick a selection just because the run seems "close to done" — if the human's pick is missing, wait for it.
