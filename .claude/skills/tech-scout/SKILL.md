---
name: tech-scout
description: |
  Run the weekly tech-research workflow: scan trusted AI/software sources for
  the past 7-14 days, score and shortlist 8-12 candidates, wait for the user's
  selection, then produce an 8-document presentation-ready research package
  (executive summary, detailed analysis, slide deck, quick-reference card,
  diagrams, Slack summary, sources, README). Orchestrates 6 phases:
  preparation, context, discovery, filtering, deep analysis, packaging,
  quality check. Stops at the end of Stage A (filtering) to wait for the
  user to pick which candidate(s) to analyze. Output language is driven
  by the --language parameter and applied via the tech-scout locale
  registry.
  Use this skill when the user invokes /tech-scout, /tech-scout-deep,
  /tech-scout-resume, or otherwise asks for a weekly tech research run.
---

# tech-scout — Weekly Tech Research Orchestrator

You are running the **tech-scout** workflow. Your job is to scan the AI/software world for the past week, surface 8-12 strong candidates for the user to choose from, then produce a polished 8-document research package on the chosen topic(s).

You run **inside Claude Code** with built-in tools (`Read`, `Write`, `Bash`, `WebSearch`, `WebFetch`, `Glob`, `Grep`, `Agent`, `AskUserQuestion`). No external API key. No new dependencies beyond what `pyproject.toml` already declares. **No external prompt file** — everything you need to run is in this skill, the per-phase reference docs, the subagent definitions, and the locale registry.

---

## Critical Rules — Read First

1. **Locale-aware text is data, not prose.** All language-dependent text
   (Stage-A selection prompt, candidate-display labels, final summary
   template) lives in `src/tech_scout/locales/`. At the start of every
   run, call `python scripts/ts_locale_info.py --code <language>` and use
   the returned `selection_prompt`, `selection_examples`,
   `final_summary_template`, and `candidate_display_labels`. Do not
   transliterate or invent locale text; do not hardcode it in your
   responses.
2. **Stage A ends at end of Phase 3 — STOP and wait for the user.**
   This is non-negotiable. The user picks; you don't pick for them. If the
   user replies ambiguously, ask for clarification before continuing.
3. **Helper scripts are deterministic.** When a step says "call
   `ts_xxx.py`", call it via `Bash` and parse the JSON envelope from
   stdout. Don't reimplement the script's logic in prose.
4. **State must be persisted.** After Phase 3 saves candidates and Phase 4
   completes, state files live in
   `<output_folder>/.tech-scout/<run-id>/`. The user may close the session
   and resume later via `/tech-scout-deep` or `/tech-scout-resume`.
5. **No fabrication.** Every URL, number, and quote in the final package
   must trace back to a real source you read. Phase 6 (quality check)
   will catch obvious lapses; preventing them is your job.

---

## Inputs

The slash command (or user) provides one or more of:

| Parameter | Default | Meaning |
|-----------|---------|---------|
| `company_name` | none | Company being researched for |
| `company_description` | none | One-line company description |
| `company_website` | none | Company website URL — used by Phase 1 when no codebase path is given |
| `codebase_path` | none | Local path to scan for tech-stack profile |
| `focus_area` | none | Narrow the sweep (e.g., `"MCP"`, `"agent infrastructure"`) |
| `time_window` | last 7 days | Date range for discovery |
| `output_folder` | from settings | Where the package will land |
| `language` | `en` | Output language (`en` / `tr` / `english` / `turkish`) |
| `slack_language` | matches `language` | Override the language of the slack-summary doc only |
| `depth` | `standard` | `light` / `standard` / `deep` |
| `prior_research_root` | parent of `output_folder` | Where past runs live (de-dup) |

If a parameter is missing, gather it as described in **Step 1** below. Don't proceed silently with bad defaults.

---

## Phase Sequence

Read the corresponding reference doc before starting each phase. They contain the full playbook; this section is the orchestration order only.

| Phase | Reference doc | Helper script(s) | Subagent? |
|-------|---------------|-------------------|-----------|
| 0 — Preparation | `reference/phase-0-preparation.md` | `ts_list_history.py`, `ts_setup_run.py`, `ts_locale_info.py` | no |
| 1 — Context | `reference/phase-1-context.md` | `ts_scan_codebase.py` (if codebase_path) | no |
| 2 — Discovery | `reference/phase-2-discovery.md` | — | yes (`tech-scout-scanner`) |
| 3 — Filtering | `reference/phase-3-filtering.md` | `ts_save_candidates.py` | no |
| **STAGE A ENDS — wait for user selection** | | | |
| 4 — Deep analysis | `reference/phase-4-analysis.md` | `ts_load_candidates.py` | yes (`tech-scout-analyzer`, one per selected candidate) |
| 5 — Packaging | `reference/phase-5-packaging.md` | `ts_render_doc.py` × 8 | no |
| 6 — Quality check | `reference/phase-6-quality-check.md` | `ts_validate_package.py` | no |

Also reference (read on first encounter):

- `reference/sources-catalog.md` — curated source list for Phase 2
- `reference/candidate-format.md` — exact rendering rules for the Stage A user-facing list
- `reference/output-templates-guide.md` — what each Jinja2 template expects

---

## Stage A — Scan & Shortlist

### Step 1: Gather missing parameters

Inspect the parameters the user supplied. For anything required and missing, use `AskUserQuestion`. The minimum to start a useful run:

- **What is your company / project name?** (free text — used to frame the package)
- **Short description** of what the company does, 1-2 sentences (helps when the web doesn't surface much).
- **Codebase path** (optional but strongly recommended). If missing, also offer:
- **Company website URL** (used as a fallback when no codebase). Phase 1 will WebFetch a few pages.
- **Focus area** (optional). Free text — narrows Phase 2 (e.g. "MCP", "agent evaluation").
- **Depth** (default `standard`).
- **Output language** (default `en`, also `tr`).

Ask only for what's missing. If the user explicitly wants "general best-of-week" mode, no company info is required — accept that and proceed.

### Step 2: Phase 0 — Preparation

Follow `reference/phase-0-preparation.md`. Outcome: a `run_id`, a `state_dir`, a list of prior topics (for de-duplication), and the active `LocaleSpec` JSON loaded into your context.

### Step 3: Phase 1 — Context

Follow `reference/phase-1-context.md`.

- If `codebase_path` is set, Bash-call `ts_scan_codebase.py` and persist the profile.
- Otherwise, if `company_website` and/or `company_name` is set, do 3-5 `WebSearch` queries plus 1-2 `WebFetch` calls on the website to build a tentative profile. Mark every claim as a guess unless you have a direct citation.
- If neither is set, switch to "general best-of-week" mode — Phase 2's scanner runs without company hints.

### Step 4: Phase 2 — Discovery

Follow `reference/phase-2-discovery.md`. Spawn the `tech-scout-scanner` subagent with the briefing payload (time_window, focus_area, company_summary, tech_stack_hints, prior_topics, language). Collect its 20-50 raw findings.

### Step 5: Phase 3 — Filtering

Follow `reference/phase-3-filtering.md`. Score each finding on Impact × Urgency × Applicability. Build a top-8-12 candidate list with diversity, then write it to JSON and call `ts_save_candidates.py`. Render the user-facing display per `reference/candidate-format.md` using the labels from the locale spec.

### Step 6: STOP

Print the user-facing display. Then print the `selection_prompt` from the active locale (verbatim from the locale spec). Then **stop**. Do not run Phase 4 until the user replies.

---

## Stage B — Deep Analysis & Package (after user picks)

The user replies (in chat, or via `/tech-scout-deep <run-id> <F-IDs>`). Resume here.

### Step 7: Parse the selection

Extract: which candidate IDs were chosen, depth override (if any), special instructions. If the user said "redo the scan with this angle: …", go back to Phase 2 with the new focus.

### Step 8: Load saved state

Bash-call `ts_load_candidates.py --run-id <id> --output-folder <folder>` to recover the full Phase 3 output. Compare against the user's IDs to make sure each pick exists.

### Step 9: Phase 4 — Deep analysis

For each chosen candidate, spawn a `tech-scout-analyzer` subagent. Run them **in parallel** if possible (multiple Agent calls in one message). Each writes its analysis JSON to `<state_dir>/analysis-<F-ID>.json`. Pass the active `language` parameter to the subagent so its body text matches the user's locale.

### Step 10: Phase 5 — Packaging

For each `OutputDocSlot` in canonical order:
1. Build the template context (combining the analysis JSONs, codebase profile, run metadata).
2. Write context to `<state_dir>/render-context-<slot>.json`.
3. Bash-call:
   `python scripts/ts_render_doc.py --slot <slot> --context-file <path> --output-folder <folder> --locale-code <code> --slack-locale-code <code> --run-id <id>`

If a render fails, fix the context (do not edit the template) and re-render that single doc. Don't restart from scratch.

### Step 11: Phase 6 — Quality check

Bash-call:
`python scripts/ts_validate_package.py --output-folder <folder> --locale-code <code> --slack-locale-code <code> --run-id <id>`

If it returns errors, regenerate the offending documents. If the validation envelope reports `passed: true` (or only warnings), proceed.

### Step 12: Final summary to user

Render the locale's `final_summary_template` with these placeholders filled in:
1. `output_folder` — absolute path
2. `three_messages` — bullet list of the three core messages
3. `single_action` — the "if you do one thing" recommendation
4. `slack_snippet` — copy-paste contents of the slack-summary doc
5. `next_week_pointer` — suggested direction for next week's run
6. `run_id`

Print and end the run.

---

## Resume Mechanics

If invoked via `/tech-scout-resume <run-id>`:

1. Read `state.json`, `candidates.json`, `selection.json` (if any), `phase-progress.json`.
2. Re-load the locale via `ts_locale_info.py --code <state.request.language>`.
3. Determine the last completed phase from `phase-progress.json`.
4. Continue from the next phase. If `selection.json` is missing and Phase 3 is complete, the user is mid-decision — re-render the candidate list and re-prompt with the locale-specific selection prompt.

---

## Hard Don'ts

- Don't render a document with unfilled `{{ ... }}` Jinja markers — the validator will flag it but better to catch yourself.
- Don't write outside `output_folder` (and its `.tech-scout/` subdir).
- Don't auto-commit anything to git. The user may want to review first.
- Don't start Phase 4 without an explicit user reply mapping to specific F-IDs.
- Don't hardcode locale-specific strings (selection prompt, labels, summary). Use what `ts_locale_info.py` returns.
- Don't mix languages in a single document; a multilingual run uses a different locale per slot, not interleaved text within one slot.
