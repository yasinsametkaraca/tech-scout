# tech-scout

> Claude Code-native plugin for weekly tech research. Scans the AI/software world,
> filters by your company context, produces a presentation-ready 8-document
> research package — in your choice of language.

[![CI](https://img.shields.io/badge/ci-passing-brightgreen)](.github/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](pyproject.toml)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

---

## What It Does

Every week, you (an AI engineer) need to answer: *"What's new in the AI world,
and which of it matters for my company?"*. Doing this by hand takes 8-12 hours.

`tech-scout` is a plugin that runs **inside Claude Code** and does the work in
two stages:

**Stage A — Scan and shortlist (~30-45 min).** It reads your codebase (optional),
sweeps trusted sources (arxiv, a16z, Hugging Face, Latent Space, GitHub Trending,
…), scores findings on **Impact × Urgency × Applicability**, then **stops and
asks you to pick** from 8-12 candidates.

**Stage B — Deep analysis and package (~30-90 min).** For your selection, it
produces a complete research package in the language you chose:

| Slot | English filename | Turkish filename | Length |
|------|------------------|------------------|--------|
| Executive summary | `00-executive-summary.md` | `00-yonetici-ozeti.md` | 5 min read |
| Detailed analysis | `01-detailed-analysis.md` | `01-detayli-analiz.md` | 30-45 min read |
| Presentation script | `02-presentation.md` | `02-sunum.md` | 12-15 min talk |
| Quick-reference card | `03-quick-reference.md` | `03-hizli-referans.md` | One page |
| Diagrams | `04-diagrams.md` | `04-gorsel-diyagramlar.md` | Visual reference |
| Slack-ready post | `05-slack-summary.md` | `05-slack-ozeti.md` | 1 min read |
| Sources & references | `06-sources.md` | `06-kaynaklar.md` | Reference |
| Package guide | `README.md` | `README.md` | Index |

---

## Language Support

The plugin ships with two locales out of the box: **English** (`en`, default)
and **Turkish** (`tr`). Adding a third locale means registering one Pydantic
spec — see [`docs/extending.md`](docs/extending.md). The chosen language drives
output filenames, validator rules, the Stage-A selection prompt, and the final
summary template.

You can also pick a different language for the Slack snippet only — useful when
the team channel reads one language but the rest of the package serves a wider
audience.

---

## How It Works (No External Prompt File)

This plugin does **not** require you to write or maintain a "research prompt"
file. Everything the workflow needs is already inside the repo:

- The **skill** (`.claude/skills/tech-scout/SKILL.md`) and per-phase reference
  docs encode the orchestration and content rules.
- **Subagent definitions** (`.claude/agents/`) encode the discovery and
  analysis playbooks.
- The **locale registry** (`src/tech_scout/locales/`) defines per-language
  filenames, labels, and prompts.
- **Templates** (`templates/<locale>/`) define output structure.

Your **per-run inputs** — what company, what codebase, what focus — come
from the slash-command parameters or, if missing, from `AskUserQuestion`
prompts the skill asks at start. No separate prompt file to maintain, no
hidden state, no env variable to set just to make the workflow runnable.

---

## Why Claude Code-Native

This plugin runs **inside your existing Claude Code subscription**. No API key,
no setup wizard, no extra account.

> Earlier drafts of this project were planned as a standalone Python application
> using FastAPI + Next.js + the Claude Agent SDK. That plan was scrapped because
> Claude Code already provides the UI, the auth, and the tools — building parallel
> infrastructure on top would have meant duplicate maintenance and forced users
> to manage an Anthropic API key separately from their existing Claude Code
> subscription.

---

## Quick Start

```bash
# 1. Clone
git clone <repo-url> tech-scout
cd tech-scout

# 2. Install Python dependencies (helpers only)
make install

# 3. (Optional) Copy .env.example → .env to set your default output root
#    and locale.
cp .env.example .env

# 4. Verify environment
make doctor

# 5. Open Claude Code in this repo (so the plugin loads).
#    Then in the chat:
#       /tech-scout
```

When you run `/tech-scout` for the first time, the skill asks for the
context it needs — company name, codebase path or website URL, focus
area, depth, language. Provide what you have, skip what you don't, and
the run starts. There's nothing else to set up.

### Slash Commands

| Command | What it does |
|---------|--------------|
| `/tech-scout` | Start a new research run (Stage A → wait for selection → Stage B) |
| `/tech-scout-deep <run-id> <F-IDs>` | Resume a saved run with a specific selection |
| `/tech-scout-list` | List past research runs |
| `/tech-scout-show <slug>` | Show summary of a past run |
| `/tech-scout-resume <run-id>` | Continue a run that was interrupted |
| `/tech-scout-doctor` | Verify environment (Python, deps, paths, locales) |

### Common Invocations

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
```

---

## How It Works — Three Layers

```
Layer 1 — Claude Code Native (orchestration, the "brain")
   Slash commands → Skill → Subagents → Reference docs
   This is where reasoning, web search, and decisions happen.
                       │
                       ▼ via Bash tool
Layer 2 — Python Helpers (deterministic glue)
   ts_scan_codebase.py  ts_setup_run.py  ts_render_doc.py
   ts_save_candidates.py  ts_validate_package.py  ts_locale_info.py …
   No LLM. Just code, JSON in, JSON out. Fully tested.
                       │
                       ▼ uses
Layer 3 — Python Library (src/tech_scout/)
   domain/  codebase/  history/  output/  state/  observability/
   locales/   ← per-locale specs (filenames, prompts, labels)
   Pure functions, dependency-injected, unit-tested.
```

See [`docs/architecture.md`](docs/architecture.md) for the full picture, including
the two-stage user flow and run-state schema.

---

## Documentation

| File | Topic |
|------|-------|
| [`docs/architecture.md`](docs/architecture.md) | Three-layer architecture, data flow, run lifecycle, locale layer |
| [`docs/usage.md`](docs/usage.md) | Slash command reference, parameters, examples |
| [`docs/observability.md`](docs/observability.md) | Audit log, run state, structured logs |
| [`docs/extending.md`](docs/extending.md) | Adding sources, custom templates, manifest readers, **new locales** |
| [`docs/faq.md`](docs/faq.md) | Common questions, troubleshooting |
| [`docs/code-standards.md`](docs/code-standards.md) | Code conventions for contributors |

---

## Roadmap (Out of Scope for v1)

- Automatic schedule (weekly cron)
- Slack/email auto-publish for the slack-summary doc
- Auto-PPTX generation from the presentation doc
- Multi-tenant / shared team runs
- PostgreSQL state backend (filesystem is enough today)

---

## License

MIT. See [`LICENSE`](LICENSE).
