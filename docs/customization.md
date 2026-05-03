# Customization

> How to change what the skill researches, how it scores, and what the
> output looks like — without writing a prompt file.

---

## Where the Workflow Lives

The plugin's behavior is split across deliberately small surfaces:

| Layer | What it controls | Where it lives |
|-------|------------------|----------------|
| **Orchestration** | Phase sequence, when to call which helper, when to stop | `.claude/skills/tech-scout/SKILL.md` |
| **Per-phase playbooks** | Detailed instructions for each of the 6 phases | `.claude/skills/tech-scout/reference/phase-N-*.md` |
| **Discovery rules** | Source priority, category coverage, output JSON shape | `.claude/agents/tech-scout-scanner.md` |
| **Analysis rules** | Reading method, depth calibration, risk/roadmap shape | `.claude/agents/tech-scout-analyzer.md` |
| **Sources catalog** | Curated list of outlets for the discovery sweep | `.claude/skills/tech-scout/reference/sources-catalog.md` |
| **Locale text** | Selection prompt, candidate-display labels, final summary | `src/tech_scout/locales/<code>.py` |
| **Output structure** | Sections in each of the 8 documents | `src/tech_scout/templates/<locale>/*.md.j2` |

There is **no external prompt file**. Per-run inputs (company, codebase,
focus, language) come from CLI flags or `AskUserQuestion` at run start.

---

## Common Customizations

### Change the discovery sources

Edit `.claude/skills/tech-scout/reference/sources-catalog.md`. The
scanner subagent reads this file each run, so no code changes are needed.

### Change the candidate-display labels (per language)

Edit the relevant locale file:

- `src/tech_scout/locales/en.py` for English
- `src/tech_scout/locales/tr.py` for Turkish

Update `_CANDIDATE_DISPLAY_LABELS`, `_SCORE_AXIS_LABELS`, or
`_FIT_LABEL_MAP`. These flow through to the Stage A user-facing display
without further changes.

### Change the verbatim Stage-A selection prompt

Edit `_SELECTION_PROMPT` in the locale file for the target language.

### Change the depth calibration table

Edit `.claude/agents/tech-scout-analyzer.md` — the "Depth Calibration"
section dictates word counts, risk counts, source counts per
`light` / `standard` / `deep`.

### Tighten the no-fabrication rules

Edit the "Hard Rules" section in
`.claude/agents/tech-scout-scanner.md` and
`.claude/agents/tech-scout-analyzer.md`.

### Change the section structure of an output document

Two places to touch:

1. The Jinja template under `src/tech_scout/templates/<locale>/` for the
   actual rendered layout.
2. The corresponding entry in `_DOCUMENTS` in `src/tech_scout/locales/<code>.py`
   if you change `min_words` or `required_section_keywords` (these drive
   the validator).

### Add an output document

See `docs/extending.md` — adding a 9th slot is one new
`OutputDocSlot` value, one new `LocaleDocumentSpec` per locale, plus the
matching templates.

### Add a new locale

See `docs/extending.md` — register one `LocaleSpec`, translate the eight
templates. No other code changes.

---

## Per-Run Customization

For one-off tweaks that don't justify a code change, use the CLI:

- `--focus "..."` narrows the discovery sweep.
- `--depth deep` makes Phase 4 more thorough.
- `--description "..."` gives the analyzer extra company-specific framing
  the codebase scan can't provide.
- `--language tr` switches the package locale.
- `--slack-language en` keeps the slack snippet in English while the rest
  of the package is Turkish.

These flow through the entire pipeline without any other configuration.

---

## When the Skill and an Agent Disagree

The skill (`SKILL.md`) wins on **orchestration** (which helper to call
when, when to stop). The agents (`agents/*.md`) win on **execution** of
their phase. Reference docs (`reference/*.md`) are the operational manual
between them.

If an instruction conflicts across layers, fix the lowest-level
authoritative source first (usually the agent definition or the
reference doc) and let upstream layers stay focused on coordination.

---

## What Not to Customize

Some surfaces are designed to stay stable; touching them creates a
maintenance tax with no upside.

- **Helper script CLI contracts.** `ts_*.py` scripts emit JSON envelopes
  with a fixed shape (`{"status": "ok|error", "data": {...}}`). The
  skill parses these. Don't add new top-level keys; don't rename
  `data` → `result`. If you genuinely need a new field, add it inside
  `data`.
- **`OutputDocSlot` enum keys.** Renaming a slot key breaks every locale
  spec and every template path. If you must rename, do all three at
  once (slot, every locale's `documents` entry, every locale's template
  filename).
- **Canonical English identifier values.** `Finding.initial_fit` ∈
  `{high, medium, low}` and `risks[].level` ∈ `{Low, Medium, High}` are
  language-neutral identifiers that the locale layer translates at
  display. Don't localize them in the analyzer JSON.
