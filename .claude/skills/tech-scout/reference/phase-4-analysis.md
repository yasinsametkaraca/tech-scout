# Phase 4 — Deep Analysis (Stage B start)

> **Goal:** For each user-selected candidate, produce a structured analysis JSON that Phase 5 templates render into the package.

## Step 1 — Parse the user's selection

The user replied to Stage A's selection prompt. Recognize the intent first; the literal phrasing varies by language.

| Reply intent | Selected IDs | Depth override |
|--------------|--------------|----------------|
| Pick one with deep override (e.g., "Go deep on F003" / "F003 derinlemesine") | `["F003"]` | `"deep"` |
| Pick one with no override (e.g., "Let's go with F001" / "F001 ile gidelim") | `["F001"]` | none |
| Pick multiple (e.g., "Run F002 and F005 together" / "F002 ve F005'i birlikte işle") | `["F002", "F005"]` | none |
| Pick multiple with explicit depth (e.g., "F003, F004, F007 standard" / "… standart") | `["F003", "F004", "F007"]` | `"standard"` |
| Re-scan with new angle (e.g., "None of these — focus on MCP" / "Hiçbiri, MCP odaklı tekrar et") | (re-scan) | (re-scan) |

If the reply is ambiguous, ask one clarifying question in the run's language — don't guess.

If the reply is "redo with this angle", go back to Phase 2 with the new `focus_area`, then Phase 3, then re-prompt.

## Step 2 — Persist the selection

Write a `UserSelection` JSON:

```jsonc
{
  "candidate_ids": ["F003"],
  "depth_override": "deep",
  "notes": "User chose F003 explicitly with deep override.",
  "decided_at": "2026-04-29T15:23:00Z"
}
```

Save to `<state_dir>/selection.json`. (Currently no helper script wraps this — write directly with the `Write` tool.)

## Step 3 — Load saved candidates

```bash
python scripts/ts_load_candidates.py \
    --run-id <run-id> \
    --output-folder "<output_folder>"
```

Validate that every selected ID exists in the loaded candidates. If one is missing, tell the user and ask again.

## Step 4 — Spawn analyzer subagent(s)

For each selected candidate, spawn `tech-scout-analyzer` (definition in
`.claude/agents/tech-scout-analyzer.md`). If multiple candidates are selected,
**spawn them in parallel** by issuing all `Agent` calls in a single
message — they run concurrently, saving wall time.

Briefing payload per candidate:

```jsonc
{
  "candidate": { /* full Candidate object from candidates.json */ },
  "depth": "deep",                                   // user's pick
  "company_name": "Acme",                             // or null
  "company_description": "AI-powered customer-support platform",
  "codebase_profile": { /* full CodebaseProfile or null */ },
  "company_context": { /* the company-context.json from Phase 1 */ },
  "language": "en",                                  // canonical 2-letter locale code
  "output_folder": "<absolute path>",
  "state_dir": "<absolute path to .tech-scout/<run-id>>"
}
```

Each subagent writes `<state_dir>/analysis-<F-ID>.json` and emits a short status line on stdout. Collect those lines for your own audit.

## Step 5 — Validate analyzer outputs

For each `<state_dir>/analysis-<F-ID>.json`:

- File exists.
- Top-level `status` field is missing or `"complete"`. (If `"incomplete"`, look at `reason` and decide whether to re-spawn or proceed with what's there.)
- All required top-level keys are present (see analyzer definition for the schema).

If a critical key is missing (e.g., `executive_summary`, `risks`, `roadmap`), re-spawn that subagent with corrective instructions.

## Step 6 — Decide on package shape

If multiple candidates were selected, the package is **one combined package** with each topic as a section in each document. Build the per-document context to merge them:

- Executive summary: one mini exec summary per topic, then a combined "single recommendation".
- Detailed analysis: each topic gets its own complete chapter.
- Presentation: combined deck — extra slides cover each topic in turn.
- Quick reference: union of concepts, top numbers, etc.
- Diagrams: union of diagrams.
- Slack summary: combined narrative naming both topics.
- Sources: union of all sources.
- README: index references both topics.

If **one** candidate was selected, the package is single-topic — simpler.

Document this decision in your audit if you wish.

## Step 7 — Build template contexts

For each `OutputDocSlot`, build the Jinja2 context dict by combining:

- The analyzer JSON(s)
- The `RunSnapshot` (`run_id`, dates, etc.)
- The `CodebaseProfile` (where relevant)
- Constants (`generated_date`, `author`, `company_name`)

See `reference/output-templates-guide.md` for what each slot's template expects. The field names are language-neutral and shared across locales — don't rename them per language.

Write each context to `<state_dir>/render-context-<slot>.json` so Phase 5
can call `ts_render_doc.py` once per slot.

## Step 8 — Hand off to Phase 5

You're done with Phase 4 when all 8 render-context JSONs exist. Move to Phase 5.

## Edge cases

- **User picks 4+ candidates** — push back in the run's language: "Combining 4 topics blows up the package size. I recommend 1-3. Which 1-3 should we keep?"
- **User picks an ID that doesn't exist** — show the valid list and ask again.
- **Analyzer subagent fails** — re-spawn once with clearer brief. If it fails again, write a partial package and tell the user which doc is incomplete.
- **Codebase profile is empty even though path was given** — Phase 1 already handled this; analyzer treats `codebase_profile: null` as generic mode.
