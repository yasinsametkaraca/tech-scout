# Architecture

> How tech-scout is organized — the three layers, the two stages, and the run state schema. Read this before changing anything non-trivial.

---

## Three Layers

```
┌──────────────────────────────────────────────────────────────┐
│ Layer 1 — Claude Code Native (orchestration "brain")         │
│   .claude/commands/*.md          (slash command entries)     │
│   .claude/skills/tech-scout/     (skill — 6-phase logic)     │
│   .claude/agents/*.md            (subagents for heavy work)  │
│   reference docs                 (per-phase playbooks)       │
│                                                              │
│   Reasoning, web search, decisions live here.                │
│   Never imports Python; never imports anything internal.     │
└────────────────────┬─────────────────────────────────────────┘
                     │ Bash tool calls into helper scripts
┌────────────────────▼─────────────────────────────────────────┐
│ Layer 2 — Helper Scripts (deterministic glue)                │
│   scripts/_common.py             (shared CLI helpers)        │
│   scripts/ts_*.py                (one entry per task)        │
│                                                              │
│   No LLM. argparse in, JSON envelope out.                    │
│   Imports from src/tech_scout/ only.                         │
└────────────────────┬─────────────────────────────────────────┘
                     │ Python imports
┌────────────────────▼─────────────────────────────────────────┐
│ Layer 3 — Library (src/tech_scout/)                          │
│   domain/        Pure data types (Pydantic), no I/O          │
│   locales/       LocaleSpec registry (filenames, prompts,    │
│                  labels per language)                        │
│   config/        Settings + structlog                        │
│   codebase/      Manifest readers, scanner, stack detector   │
│   history/       Past-run repository, overlap detection      │
│   output/        Jinja2 renderer, slug, validator            │
│   state/         JSON state read/write                       │
│   observability/ Audit log, correlation                      │
│   utils/         Time, path-safety helpers                   │
│                                                              │
│   Pure Python. Dependency-injected. Fully unit tested.       │
└──────────────────────────────────────────────────────────────┘
```

**Dependency direction is always downward.** Layer 1 calls Layer 2 via shell. Layer 2 imports Layer 3. Layer 3 has no internal upward dependencies. Within Layer 3, `domain/` depends on nothing internal; `locales/` depends only on `domain/`; everything else may depend on both.

---

## Two Stages, Six Phases

A run goes through six phases split across two stages, with a hard stop in the middle for user input.

```
                              [User runs /tech-scout]
                                       │
                                       ▼
                ┌──────────────────────────────────────────┐
   Stage A      │  Phase 0  Preparation                     │
                │  Phase 1  Context (codebase / web / none) │
   ~30-45 min   │  Phase 2  Discovery (subagent: scanner)   │
                │  Phase 3  Filtering & Shortlist           │
                └──────────────────────┬───────────────────┘
                                       │
                                       ▼
                                  ┌────────┐
                                  │  STOP  │  prints 8-12 candidates
                                  │ wait   │  + selection prompt
                                  └────┬───┘
                                       │
                                  user picks
                                       │
                                       ▼
                ┌──────────────────────────────────────────┐
   Stage B      │  Phase 4  Deep Analysis (subagent per    │
                │           selected candidate, parallel)  │
   ~30-90 min   │  Phase 5  Packaging (8 docs)             │
                │  Phase 6  Quality check (validator)      │
                └──────────────────────┬───────────────────┘
                                       │
                                       ▼
                            [Final summary to user]
```

The skill's `SKILL.md` describes the orchestration; per-phase playbooks live in `reference/phase-N-*.md`.

---

## Run State

Every run gets a state directory:

```
<output_folder>/.tech-scout/<run-id>/
├── state.json              ResearchRequest + RunSnapshot
├── candidates.json         CandidateList (Phase 3 output)
├── selection.json          UserSelection (after Stage A pick)
├── codebase-profile.json   CodebaseProfile (if codebase scanned)
├── analysis-<F-ID>.json    Per-candidate analysis (Phase 4 output)
├── render-context-<doc>    Per-document Jinja2 context (Phase 5 input)
├── phase-progress.json     Phase status — for resume
└── audit.jsonl             Append-only event log
```

This is what makes the run **resumable**. A user can close their terminal at any time and continue with `/tech-scout-resume <run-id>` later.

`run-id` format: `YYYY-MM-DD-<6-12 char alphanumeric slug>`.

---

## Why This Shape

### Why not a single Python application

We initially planned standalone Python with FastAPI + Next.js + Claude Agent SDK. That mistake was caught during planning. The user runs in **Claude Code**. Claude Code already provides:

- The chat UI (no need to build one)
- The web/file/bash tools (no need to wrap an SDK)
- Authentication (via the user's existing subscription — no API key)

Building parallel infrastructure on top would have meant duplicate UI, duplicate auth surface, and forcing the user to manage a separate Anthropic API key. None of that adds value.

### Why a skill plus subagents

Discovery and deep analysis each consume a lot of context. Doing them in the parent (skill) context shifts thousands of tokens of intermediate text into the main session. Subagents run in their own context and return only the structured summary.

### Why helper scripts

Three reasons:

1. **Determinism.** Slug generation, manifest parsing, JSON validation, file I/O — none of these benefit from LLM judgment. They benefit from being tested.
2. **Testability.** Helpers are CLI commands; integration tests run them as subprocesses with real filesystem fixtures.
3. **Clarity of contract.** When the skill says "call `ts_setup_run.py`", the contract is the script's `--help`. No ambiguity about what the LLM is "supposed to do" deterministically.

### Why JSON envelopes

Every helper emits `{"status": "ok"|"error", "data": {...}}`. This makes the skill's parsing logic uniform: never wonder which script returns which shape. `_common.py::run_script` enforces the convention.

---

## Critical Files

| Path | Why critical |
|------|--------------|
| `.claude/skills/tech-scout/SKILL.md` | Top-level orchestration. The phase sequence and "stop after Phase 3" rule live here. |
| `.claude/skills/tech-scout/reference/phase-3-filtering.md` | Stage A endpoint logic. Mistakes here break the entire two-stage flow. |
| `.claude/agents/tech-scout-scanner.md` | Discovery subagent. Quality of week's findings depends on this being focused and honest. |
| `.claude/agents/tech-scout-analyzer.md` | Per-topic analysis subagent. Output quality directly determines package quality. |
| `templates/<locale>/01-detailed-analysis.md.j2` (and TR equivalent) | The longest, highest-stakes template. Sets the analysis-doc quality bar. |
| `src/tech_scout/locales/registry.py` | Locale registry. Filenames, validator rules, prompts, and labels for every language come from here. |
| `src/tech_scout/output/validator.py` | The safety net for Phase 6. Tighter rules here = fewer broken packages. |
| `src/tech_scout/codebase/stack_detector.py` | Phase 1's quality limits how relevant Phase 2's findings are. |

---

## Locale Layer

Output language is data, not branching logic. Each registered locale is a
single :class:`LocaleSpec` instance under `src/tech_scout/locales/`:

```
locales/
  spec.py        LocaleSpec (frozen Pydantic), LocaleDocumentSpec
  registry.py    LocaleRegistry, get_locale(), DEFAULT_LOCALE_CODE
  en.py          English LocaleSpec (default)
  tr.py          Turkish LocaleSpec
```

A `LocaleSpec` declares:

- The two-letter `code`, `display_name`, and `aliases` (e.g. `english`).
- The matching `Language` enum value.
- The `template_subdir` under `templates/`.
- One `LocaleDocumentSpec` per `OutputDocSlot` (filename, template filename,
  min word count, required-section keywords).
- The verbatim Stage-A `selection_prompt`.
- The `final_summary_template` for Phase 6.
- Display labels (`candidate_display_labels`, `score_axis_labels`,
  `fit_label_map`).

Helper scripts surface the registry over JSON via `ts_locale_info.py`. The
skill calls it once per run and uses the returned data so no
locale-specific text is hardcoded in markdown.

Adding a third locale takes one new file (`locales/<code>.py`), an entry in
`locales/registry.py`, and a `templates/<code>/` directory with the eight
templates. No other code changes.

---

## Where to Read Next

- `usage.md` — slash command reference, parameter details
- `observability.md` — audit log shape, structured logging conventions
- `extending.md` — adding new manifest readers, new output documents, new sources
- `faq.md` — common questions, troubleshooting
