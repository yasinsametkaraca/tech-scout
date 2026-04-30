# FAQ

> Common questions and troubleshooting.

---

## Setup

### Q: Do I need an Anthropic API key?

**A:** No. The plugin runs inside Claude Code and uses your existing subscription. There's no separate API key, no billing setup, no environment variable to manage.

### Q: Do I need Node.js?

**A:** No. The plugin is pure Python (3.10+) plus markdown definitions for Claude Code. Templates use Jinja2, not anything Node-related.

### Q: How do I install?

**A:**

```bash
git clone <repo-url> ~/Documents/Github/tech-scout
cd ~/Documents/Github/tech-scout
make install-dev   # installs Python deps + pre-commit hooks
```

Then open the repo in Claude Code (the `.claude/` directory auto-loads). Type `/tech-scout-doctor` to verify.

### Q: I just cloned the repo. What do I need to set up before running?

**A:** Almost nothing. The plugin doesn't use a separate prompt template
file — everything the workflow needs is already in `.claude/` (skill,
references, subagents) and `src/tech_scout/locales/` (per-language
text). Just:

1. `make install` (or `pip install -e .`) for the Python helpers.
2. (Optional) `cp .env.example .env` and edit `TECH_SCOUT_DEFAULT_OUTPUT_ROOT`.
3. `/tech-scout` in Claude Code — the skill asks you for company name,
   codebase path, focus area, depth, and language interactively if you
   don't pass them as flags.

---

## Running

### Q: I ran `/tech-scout` and it just stopped after showing 8 candidates. Did it crash?

**A:** No — that's the design. Stage A ends with the candidate display. The skill is **waiting for your reply**. Tell it which candidate(s) you want analyzed:

```text
Go deep on F003
```

…or any of the other reply formats listed in the selection prompt (the prompt
itself is rendered in the run's language).

### Q: How do I cancel a run mid-way?

**A:** Just close the chat or press Ctrl+C in the terminal. The state is persisted; you can resume later with `/tech-scout-resume <run-id>` or start fresh.

### Q: Will it spend money if I forget about it?

**A:** Cost is bounded by your Claude Code subscription's normal limits — there's no separate metering. A `deep` run consumes more context than a `light` run, but neither makes API calls outside your subscription.

### Q: How do I run multiple research tracks per week?

**A:** Run `/tech-scout` multiple times. Each gets its own run-id and output folder. They don't conflict.

---

## Output

### Q: Why are some files in Turkish and some in English?

**A:** Two reasons it can happen by design, and one bug case:

1. **You used `--slack-language` to override the slack-summary doc only.** That's intentional — the slack snippet can target a different audience than the rest of the package.
2. **The package mixes locales because you ran two separate runs into the same folder.** Each run produces its own filenames; check the run-id in `.tech-scout/`.
3. **Bug:** within one slot, body prose is in two languages. File an issue with the run-id — the analyzer subagent should pick one language and stick to it.

### Q: The detailed analysis is shorter than expected.

**A:** Probably you ran with `--depth light`. Switch to `--depth standard` (default) or `--depth deep` for longer analyses. The detailed-analysis filename is `01-detailed-analysis.md` for English runs and `01-detayli-analiz.md` for Turkish runs.

### Q: Can I edit the package files after they're generated?

**A:** Yes. They're plain markdown. Your edits won't be touched unless you re-run for the same run-id (which you usually wouldn't).

### Q: How do I share a package with a teammate?

**A:** Just send them the folder. Or commit it to a shared repo. The folder is self-contained except for the `.tech-scout/` subfolder (which is gitignored — that's run state, not deliverables).

---

## Troubleshooting

### Q: Doctor says "Templates directory does not exist".

**A:** The `templates/` folder is missing from your checkout. Re-clone or `git pull`. If you intentionally moved it, set `TECH_SCOUT_TEMPLATES_DIR=/your/path`.

### Q: Doctor says "Python 3.10+ required".

**A:** You're on Python 3.9 or older. Install 3.10+ — `pyenv install 3.12.4` is one easy path.

### Q: A helper script returns `{"status": "error"}` but I don't understand why.

**A:** The `data` field has the error type, message, and context. Common categories:

- `CodebaseScanError` — given codebase path is wrong or unreadable.
- `StateStoreError` — run-id mismatch, malformed state file.
- `TemplateRenderError` — context dict missing a required field.
- `ValidationError` — Phase 6 caught a structural problem.
- `HistoryLookupError` — past-runs root not found.

Look at `data.context` for specifics.

### Q: The validator complains about "Unrendered Jinja2 markers".

**A:** Phase 5 rendered a template but a context field was missing or evaluated to a Jinja expression. Check `<state_dir>/render-context-<doc>.json` for missing keys, then re-run that single render. The skill's Phase 5 playbook covers the fix flow.

### Q: The scanner returned only 5 findings.

**A:** Common causes:

- Time window too narrow. Default is 7 days; set `--time-window` if you have it (or just rerun next week).
- Focus area too tight. Drop `--focus` and rerun.
- Network issues for WebSearch / WebFetch. Check Claude Code's status panel.

The skill's Phase 2 playbook describes how to broaden a sweep.

### Q: I get "Run-id not found" with `/tech-scout-resume`.

**A:** The run state is in a different output folder than the default. Pass `--output PATH` pointing to the correct folder. List available run-ids:

```bash
ls -d <output_root>/*/.tech-scout/*/
```

### Q: I want to re-run Stage B for the same selection without re-running Stage A.

**A:**

```text
/tech-scout-deep <run-id> <F-IDs>
```

This skips Phases 0-3 and goes straight to Phase 4 with the saved candidates.

### Q: The skill picked a candidate without my input.

**A:** That's a bug. The whole point of the two-stage design is that the user picks. File an issue with the run-id; the skill should be reminding itself "STOP" at end of Phase 3.

---

## Customization

### Q: Can I add a new source to the discovery sweep?

**A:** Yes. Edit `.claude/skills/tech-scout/reference/sources-catalog.md`. The scanner reads this on every run.

### Q: Can I change the candidate display format?

**A:** Yes. Edit `.claude/skills/tech-scout/reference/candidate-format.md`. The skill follows whatever's there.

### Q: Can I add a 9th output document?

**A:** Yes. See `extending.md` for the step-by-step.

### Q: Can I run on Linux/macOS?

**A:** Yes. The Python lib is OS-agnostic. The default `default_output_root` is `~/tech-scout-runs`, which works on every platform. Override anything else via env vars or your own `.env`.

### Q: How do I add a new output language?

**A:** Register a new `LocaleSpec`:

1. Create `src/tech_scout/locales/<code>.py` mirroring `en.py` (English) — it's the canonical reference. Translate every string field.
2. Add the new instance to `src/tech_scout/locales/registry.py`.
3. Create `templates/<code>/` and translate the eight templates from `templates/en/` (preserving Jinja field names).
4. Run `make doctor` and `make test` — both should pass with no other code changes.

See `docs/extending.md` for the worked example.

---

## Philosophy

### Q: Why two stages instead of one?

**A:** Because surveying the AI ecosystem usefully requires *judgment about what matters this week*, and that judgment is the user's. Picking automatically would either be wrong (forced rule-based picks) or too unpredictable (LLM picks may not match the user's actual interest). Showing 8-12 strong candidates and letting the user pick gives the human the steering wheel where it matters.

### Q: Why so much markdown and so little Python?

**A:** Because LLMs follow markdown instructions reliably when the instructions are clear, and editing markdown is faster than refactoring code. Python exists precisely where determinism matters (file I/O, parsing, validation). The boundary is intentional. See `customization.md` for what each markdown surface controls and how to safely edit it.

### Q: Why isn't there a Web UI?

**A:** Because Claude Code already provides one (the chat panel). Adding a separate Web UI would mean duplicate maintenance, duplicate auth, and forcing users to manage an Anthropic API key separately from their Claude Code subscription. Avoiding all of that was the entire point of being "Claude Code-native".
