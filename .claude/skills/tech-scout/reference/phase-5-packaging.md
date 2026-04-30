# Phase 5 — Packaging

> **Goal:** Render the 8 documents into the output folder. Deterministic step — no LLM creativity here, just template rendering with the contexts Phase 4 built and the active locale's filenames + templates.

## Step 1 — Confirm context files

For each `OutputDocSlot` in canonical order, the file
`<state_dir>/render-context-<slot>.json` must exist. If any is missing,
go back to Phase 4 step 7 and produce it.

The order:

1. `executive_summary`
2. `detailed_analysis`
3. `presentation`
4. `quick_reference`
5. `diagrams`
6. `slack_summary`
7. `sources`
8. `readme`

## Step 2 — Render each slot

For each slot in order, run:

```bash
python scripts/ts_render_doc.py \
    --slot <slot> \
    --context-file "<state_dir>/render-context-<slot>.json" \
    --output-folder "<output_folder>" \
    --locale-code <code> \
    --slack-locale-code <code> \
    --run-id <run-id>
```

The helper:
- Resolves the locale (and slack locale) via the registry.
- Loads the templates root from settings (or `--templates-root`).
- Validates the JSON context.
- Renders `templates/<locale.template_subdir>/<slot's template filename>` with strict undefined (missing fields raise).
- Writes the markdown to `<output_folder>/<locale's slot filename>`.
- Emits a `doc_rendered` audit event including the slot, filename, and locale code.

Parse the JSON envelope. On success the response is:

```json
{
  "status": "ok",
  "data": {
    "slot": "executive_summary",
    "filename": "00-executive-summary.md",
    "locale_code": "en",
    "written_path": "...",
    "templates_root": "..."
  }
}
```

## Step 3 — Handle render errors

Most failures are **missing context fields** — the template needs
`{{ topic_title }}` but the context didn't provide it. The error message
will name the missing variable.

To fix:
1. Open the offending render-context file.
2. Add the missing field with a sensible value (look up in the analysis JSON).
3. Re-run the helper for that single slot.

Do **not** edit the template. Templates are stable; contexts vary.

If you can't find a sensible value:
- For optional human-friendly fields, supply a brief placeholder (e.g. `"-"` or a short "TBD" in the run's language).
- For structural fields (lists, required sections), this is a real error
  — go back to Phase 4 and re-spawn the analyzer with instructions to
  fill that field.

## Step 4 — Optional folder rename

The Phase 0 default output folder used a placeholder slug
(`<YYYY-MM-DD>-pending`). Now that you know the topic, rename to:

```
<YYYY-MM-DD>-<topic-slug>
```

Where `topic-slug` is a slugified version of the package title. You can
generate it via:

```python
from tech_scout.output.slug import slugify_topic
slug = slugify_topic("AutoHarness x Acme")
```

(Run via `python -c "..."` in a Bash call, or simply slugify in your
head — the title is short.)

If you rename, **update**:
- `state.json.request.output_folder`
- The path in any audit log entries you emit henceforth (just for
  consistency — old entries with the old path are fine; audit is
  append-only).

If renaming is risky (path on a shared drive, files locked, etc.), skip
it. The package works fine in the placeholder folder.

## Step 5 — Hand off to Phase 6

When all 8 files exist on disk, proceed to Phase 6.

## Performance notes

Each render takes 1-3 seconds. Eight slots ≈ 15-25 seconds total.
Running the helpers in parallel via Bash is rarely worth the
orchestration complexity at this scale.

## Why so much can go wrong here despite being "just render"

- Subtle Jinja2 syntax mistakes in custom contexts.
- Missing optional fields that the template expected as required.
- Encoding issues if the analyzer output had Windows-style line endings.
- Locale code typos — if `--locale-code xx` is unknown, the helper
  errors clearly. If it is known but maps to a wrong locale, you'll see
  the wrong filename pattern; cross-check against `ts_locale_info.py`.

Phase 6 will catch the most obvious issues. Your job in Phase 5 is to
get all 8 files on disk; perfection isn't required yet.
