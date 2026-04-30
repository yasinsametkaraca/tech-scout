---
description: Run a weekly tech research run — Stage A (scan + shortlist) then wait for the user's selection, then Stage B (deep analysis + 8-document package).
argument-hint: '[--company NAME] [--description "TEXT"] [--website URL] [--codebase PATH] [--focus AREA] [--depth light|standard|deep] [--language en|tr] [--output PATH]'
---

# /tech-scout — Weekly Tech Research

You are about to run the **tech-scout** workflow. Invoke the `tech-scout` skill (in `.claude/skills/tech-scout/SKILL.md`) with the parameters parsed from the user's invocation.

## Argument parsing

The user may have supplied any combination of:

| Flag | Default | Meaning |
|------|---------|---------|
| `--company NAME` | none | Company / project being researched for |
| `--description "TEXT"` | none | One-line description of what the company does |
| `--website URL` | none | Company website URL — Phase 1 will WebFetch it for domain context when no `--codebase` is given |
| `--codebase PATH` | none | Local codebase path to scan in Phase 1 (highest-signal source) |
| `--focus AREA` | none | Narrow the discovery sweep |
| `--depth light\|standard\|deep` | `standard` | Stage B depth |
| `--language en\|tr\|english\|turkish` | `en` (English) | Output language |
| `--slack-language en\|tr\|english\|turkish` | matches `--language` | Slack snippet language only |
| `--output PATH` | configured default | Where the package will be written |
| `--prior-research PATH` | parent of `--output` | Where past runs live (for de-dup) |

If any required parameter is missing and you need it to start, use `AskUserQuestion`. The minimum context the skill needs is:

- A company / project name (or explicit "general best-of-week" mode)
- At least **one** of: codebase path, website URL, or a description — any one of these is enough to ground Phase 1

User's raw arguments: $ARGUMENTS

## What to do

1. **Read the skill** at `.claude/skills/tech-scout/SKILL.md`. Follow its phase sequence.
2. **Gather missing parameters via `AskUserQuestion`** (skill Step 1).
3. **Run Stage A** (Phases 0-3): preparation → context → discovery → filtering. End with the user-facing candidate display per `reference/candidate-format.md` using the active locale's labels.
4. **STOP** at end of Stage A. Wait for the user to select candidates and depth. Don't pre-emptively continue — even if the user is impatient, ask one clarifying question rather than guessing.
5. When the user replies with their selection, **resume into Stage B** (Phases 4-6) and produce the package.

## Hard rules

- Never auto-pick a candidate. The user picks.
- Helper scripts are deterministic — when the skill says "call `ts_xxx.py`", do it via Bash and parse the JSON envelope.
- Persist state under `<output>/.tech-scout/<run-id>/` so the run can be resumed.
- No fabricated URLs, numbers, or quotes. Phase 6 will catch obvious lapses.
- Locale-specific text (selection prompt, labels, summary template) comes from `ts_locale_info.py` — never hardcode.

## On error

If any helper script fails (status: error envelope), surface the error message to the user, suggest the most likely fix, and don't proceed.

If the skill encounters an unrecoverable issue mid-Phase 4 (analyzer subagent fails twice), write what you have to disk and tell the user the package is partial.

## Begin

Invoke the skill now and start Phase 0.
