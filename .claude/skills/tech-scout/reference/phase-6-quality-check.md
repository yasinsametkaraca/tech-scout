# Phase 6 — Quality Check

> **Goal:** Verify the package is structurally complete and the content meets baseline quality. Run the validator with the active locale; act on any errors.

## Step 1 — Run the validator

```bash
python scripts/ts_validate_package.py \
    --output-folder "<output_folder>" \
    --locale-code <code> \
    --slack-locale-code <code> \
    --run-id <run-id>
```

The helper returns a JSON envelope with the validation report:

```json
{
  "status": "ok",
  "data": {
    "package_path": "...",
    "locale_code": "en",
    "slack_locale_code": "en",
    "passed": true,
    "error_count": 0,
    "warning_count": 2,
    "documents_present": ["00-executive-summary.md", "..."],
    "documents_missing": [],
    "issues": [
      {
        "severity": "warning",
        "document": "01-detailed-analysis.md",
        "section": null,
        "message": "Document is shorter than expected minimum: 1280 words < 1500 expected"
      }
    ]
  }
}
```

If `data.passed` is `true`, you're done — proceed to the final summary.

If `data.passed` is `false` (or the helper exits non-zero with a
`"status": "error"` envelope), fix the issues per below.

## Step 2 — Triage issues

| Issue | Action |
|-------|--------|
| `Required document missing: <name>` | Re-render that single slot per Phase 5 step 2. |
| `No markdown heading found` | Document is empty or rendered to garbage; re-render with a corrected context. |
| `Unrendered Jinja2 markers found` | Render failed silently; re-run `ts_render_doc.py` for that slot. |
| `Document is shorter than expected minimum` (warning) | If it's the executive summary or quick reference, that's intentionally short — ignore. For the detailed analysis, ask the analyzer subagent to expand and re-render. |
| `Expected section keyword not found: 'X'` (warning) | Ask the analyzer to add the missing section, then re-render. The keyword is whatever the active locale lists in its `required_section_keywords`. |
| `No mermaid diagram fences found` (warning, diagrams doc) | Ask analyzer to provide at least 1-2 mermaid diagrams. |
| `No markdown links found` (warning, sources doc) | The references section is incomplete; analyzer should fix. |
| `Cannot read document: <error>` | Filesystem issue (permissions, encoding) — investigate. |

## Step 3 — Re-render only what's broken

When you fix a context and re-render one slot, the others stay intact.
Run the validator again — it's cheap.

## Step 4 — When to stop iterating

- All errors fixed → stop, you're done.
- Only warnings remain → judgment call. If they're cosmetic (a section title not found because the analyzer used a synonym), accept them. Document the decision in the audit log.
- After 2-3 fix cycles, still failing → escalate to user: "Validation has these residual issues; do you want to ship as-is or have me regenerate?"

## Step 5 — Final summary to the user

Render the active locale's `final_summary_template` (loaded in Phase 0
via `ts_locale_info.py`). It uses these placeholders:

- `{output_folder}` — absolute path
- `{three_messages}` — bullet list (one per line, e.g., `1. … 2. … 3. …`)
- `{single_action}` — one-line "if you do one thing" recommendation
- `{slack_snippet}` — paste the contents of the slack-summary doc as a fenced code block
- `{next_week_pointer}` — short paragraph or bullets
- `{run_id}` — the run id

Substitute the values into the template, print it, and end the run.

Use the language the user picked. Do not invent locale-specific strings; if a placeholder is empty, fill it with a short literal in the run's language (e.g., "—" or a single line of "TBD"-equivalent).

## Performance

Validation takes ~1 second. Re-rendering one slot is 1-3 seconds. Even
with three fix cycles you're well under a minute.

## When validation can't catch problems

The validator checks structure, not truth. It does not check:

- Whether claimed numbers are real.
- Whether linked URLs resolve.
- Whether the analysis's reasoning is sound.

These are the analyzer subagent's responsibility (it has explicit "no
fabrication" rules). If you suspect a fabricated number or quote, flag
it to the user and re-spawn the analyzer with stricter instructions.
