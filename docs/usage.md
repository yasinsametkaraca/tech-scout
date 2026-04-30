# Usage

> Slash command reference, parameter conventions, and example invocations.

---

## Quick Start

```text
/tech-scout
```

That's it. The skill prompts you for missing parameters via `AskUserQuestion`, runs Stage A, prints 8-12 candidates, then waits. You reply, it runs Stage B. Done.

---

## Slash Commands

### `/tech-scout`

Start a new research run. Goes through Stages A and B.

```text
/tech-scout [--company NAME] [--description "TEXT"] [--website URL]
            [--codebase PATH] [--focus AREA]
            [--depth light|standard|deep]
            [--language en|tr] [--slack-language en|tr]
            [--output PATH] [--prior-research PATH]
```

#### Parameters

| Flag | Default | Notes |
|------|---------|-------|
| `--company NAME` | — | Company / project name. Drives company-specific framing. |
| `--description "TEXT"` | — | One-line description. Helps when web doesn't surface much. |
| `--website URL` | — | Company website. Phase 1 fetches it for domain context when no `--codebase` is given. |
| `--codebase PATH` | — | Local codebase root. Phase 1 will scan it (highest-signal source). |
| `--focus AREA` | — | Narrow the discovery sweep (`"MCP"`, `"agent infrastructure"`). |
| `--depth` | `standard` | `light` (15-25 min Stage B) / `standard` (30-45 min) / `deep` (60-90 min). |
| `--language` | `en` | Output language. Accepts `en` / `tr` / `english` / `turkish`. |
| `--slack-language` | matches `--language` | Override the language of the slack-summary doc only. |
| `--output PATH` | configured default | Where the package will land. |
| `--prior-research PATH` | parent of `--output` | Where past runs live (de-dup). |

If you skip parameters, the skill asks for them via `AskUserQuestion` at start. The minimum context the workflow needs:
- A company / project name (or explicit "general best-of-week" mode)
- At least one of: `--codebase`, `--website`, or `--description`

#### Examples

```text
# Full English run with codebase scan, focused on MCP, deep analysis
/tech-scout --company Acme
            --codebase /path/to/your-codebase
            --focus "MCP and tool integration"
            --depth deep

# No codebase — give the website instead
/tech-scout --company Acme
            --website https://acme.example.com
            --description "AI customer support platform"

# Quick general run, no company context
/tech-scout --depth light

# Turkish package, English Slack snippet
/tech-scout --company Acme --language tr --slack-language en

# Different company, no codebase, English
/tech-scout --company Acme
            --description "AI customer support platform"
            --focus "agent evaluation"
```

### `/tech-scout-deep`

Resume Stage B with a specific selection (skip Stage A — the candidates must already be saved).

```text
/tech-scout-deep <run-id> <F-IDs comma-separated> [--depth ...] [--output PATH]
```

Examples:

```text
/tech-scout-deep 2026-04-29-abc123 F003
/tech-scout-deep 2026-04-29-abc123 F001,F005 --depth deep
```

### `/tech-scout-list`

List past research runs. Read-only.

```text
/tech-scout-list [--root PATH] [--limit N]
```

Default: shows 20 most recent from the configured research root.

### `/tech-scout-show`

Display summary of a past run — the executive summary, Slack snippet, key references.

```text
/tech-scout-show <slug-or-folder-name> [--root PATH]
```

Example:

```text
/tech-scout-show memory-layer-ai-agents
/tech-scout-show 2026-04-22-memory-layer-ai-agents
```

### `/tech-scout-resume`

Continue an interrupted run. Reads phase progress and picks up where it left off.

```text
/tech-scout-resume <run-id> [--output PATH]
```

If the run was interrupted mid-Stage-A (after candidates were saved but before you replied), this re-prints the candidate list and prompts again — in the locale you originally chose for that run.

### `/tech-scout-doctor`

Verify your environment. Run this first if anything seems off.

```text
/tech-scout-doctor
```

Checks: Python version, all required deps, templates dir, **per-locale template completeness**, skill reference dir, output root writability.

---

## Output Folder Layout

After a successful English run you'll find:

```
<output_folder>/<YYYY-MM-DD>-<topic-slug>/
├── 00-executive-summary.md      Manager / non-technical, ~5 min read
├── 01-detailed-analysis.md      Engineering team, full analysis
├── 02-presentation.md           Slide-by-slide presentation script
├── 03-quick-reference.md        One-page Q&A card for the talk
├── 04-diagrams.md               Mermaid + ASCII diagrams
├── 05-slack-summary.md          Channel-ready 200-300 word post
├── 06-sources.md                Primary + secondary sources
├── README.md                    Package guide
└── .tech-scout/                 Run state (gitignored)
    └── <run-id>/
        ├── state.json
        ├── candidates.json
        ├── selection.json
        ├── codebase-profile.json
        ├── analysis-<F-ID>.json
        ├── render-context-<slot>.json
        ├── phase-progress.json
        └── audit.jsonl
```

Turkish runs use the corresponding Turkish filenames (`00-yonetici-ozeti.md`, …). The `slack_summary` slot can use a different locale than the rest of the package; its filename then matches the slack locale.

---

## Cost / Time Expectations

| Depth | Stage A | Stage B | Total |
|-------|---------|---------|-------|
| `light` | ~20-30 min | ~15-25 min | ~35-55 min |
| `standard` | ~30-45 min | ~30-45 min | ~60-90 min |
| `deep` | ~30-45 min | ~60-90 min | ~90-135 min |

These are wall-clock estimates. They depend on web latency for the discovery sweep and how thorough the analyzer subagent is.

Cost is bounded by your Claude Code subscription — there's no separate API metering.

---

## When Things Go Wrong

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `/tech-scout-doctor` shows "import X failed" | Deps not installed | `make install-dev` |
| `/tech-scout-doctor` shows "Locale '<code>' is missing template(s)" | Per-locale template file missing | Restore from git or your fork; each locale needs all 8 templates under `templates/<code>/`. |
| Phase 2 returns 0 findings | Time window too narrow / focus too tight | Re-run with `--focus` removed |
| Phase 6 fails with "Unrendered Jinja2 markers" | Render context was missing fields | Skill should re-render that one doc; if it can't, send the analyzer back to fill the missing fields |
| Run gets stuck after Stage A | The skill is correctly waiting for your selection | Reply with the F-IDs you want |
| `/tech-scout-resume` says run-id not found | Wrong output folder | Pass `--output PATH` pointing to the correct folder |
| Unknown locale code error | Typo in `--language` | Use `en`, `tr`, `english`, or `turkish` (see `python scripts/ts_locale_info.py --list`) |
