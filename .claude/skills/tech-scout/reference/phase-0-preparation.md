# Phase 0 — Preparation

> **Goal:** Establish identity for the run (a fresh `run_id`), figure out where output goes, learn what topics have already been covered (so we don't repeat them), and load the active locale spec into context.

## Inputs

From the parameters supplied by the user / slash command (collect any missing required values via `AskUserQuestion` per the skill's Step 1):

- `output_folder` (may be unset — derive a default below)
- `prior_research_root` (may be unset — defaults to the parent of `output_folder`)
- `language` — defaults to `en`. Accepts `en` / `tr` / `english` / `turkish`.
- `slack_language` — defaults to `language`.
- `company_name`, `company_description`, `company_website`, `codebase_path`, `focus_area`, `depth` — pass through to `ts_setup_run.py`

## Steps

### 1. Derive `output_folder` if missing

Default rule:

```
<prior_research_root>/<YYYY-MM-DD>-<placeholder>/
```

Where `<placeholder>` is a short slug like `pending` — we don't know the topic yet. Phase 5 may rename the folder once a topic is chosen.

If the user didn't pass an `output_folder`, derive one from `Settings.default_output_root` (configurable via `TECH_SCOUT_DEFAULT_OUTPUT_ROOT`). If that path doesn't exist or isn't right, ask the user via `AskUserQuestion`.

### 2. List prior research

Bash:

```bash
python scripts/ts_list_history.py "<prior_research_root>" --limit 30
```

Parse the JSON envelope. Extract titles + primary_topics from the most recent entries (≈ last 6-10 weeks). Hold them in memory to pass to Phase 2's subagent so it avoids duplicating last week's topic.

If the root doesn't exist yet, the script returns an empty list. That's fine — first-week run.

### 3. Set up the run

Bash:

```bash
python scripts/ts_setup_run.py \
    --output-folder "<output_folder>" \
    [--company-name "..."] \
    [--company-description "..."] \
    [--company-website "https://..."] \
    [--codebase-path "..."] \
    [--focus-area "..."] \
    --depth <light|standard|deep> \
    --language <en|tr|english|turkish> \
    --slack-language <en|tr|english|turkish> \
    [--prior-research-root "<path>"]
```

The script:
- Creates `output_folder` if needed.
- Creates `<output_folder>/.tech-scout/<run-id>/` with a fresh `run_id` (unless one already exists for this folder, in which case it returns the existing ID — useful for retries).
- Writes `state.json` with the validated `ResearchRequest` and a fresh `RunSnapshot`.
- Initializes `audit.jsonl` with a `run_initialized` event.
- Returns the canonical `locale_code` and `slack_locale_code` after alias normalization.

Capture from the JSON envelope:
- `run_id`
- `state_dir`
- `locale_code` and `slack_locale_code`
- whether the script reused an existing run (`reused: true/false`)

### 4. Load the active locale spec

Bash:

```bash
python scripts/ts_locale_info.py --code <locale_code>
```

Parse the JSON envelope. The `data.spec` is the locale data you'll use throughout the run:

- `selection_prompt` — verbatim text printed at end of Stage A
- `selection_examples` — example user replies (for nudging the user if their reply is ambiguous)
- `final_summary_template` — Phase 6 wrap-up template
- `candidate_display_labels`, `score_axis_labels`, `fit_label_map` — labels for the Stage A candidate display
- `documents` — slot → filename mapping (used by Phases 5 and 6)

If `slack_locale_code` differs from `locale_code`, also load that spec — you'll use it only for the `slack_summary` slot.

### 5. Bind the run id

For your own logging (so subsequent helper calls log under the same run):

```bash
export TECH_SCOUT_RUN_ID=<run-id>
```

(Optional — helper scripts accept `--run-id` explicitly. The env var is just convenience.)

## Outputs You Carry to Phase 1

- `run_id`, `state_dir`, `output_folder`
- `locale_spec` (and `slack_locale_spec` if different)
- `prior_topics` (list of strings, may be empty)

## Failure Modes

- `ts_list_history.py` returns an error → log it, treat as empty history, continue.
- `ts_setup_run.py` returns an error → bubble up to user. Don't continue silently.
- `ts_locale_info.py` returns an error → the requested locale isn't registered. Tell the user the available codes (the error envelope lists them) and ask which one they meant.
- `output_folder` is on a read-only filesystem → ask the user for an alternative.
