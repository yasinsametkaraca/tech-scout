# Phase 2 — Discovery

> **Goal:** Sweep the AI/software ecosystem for candidates worth analyzing. Done by spawning the `tech-scout-scanner` subagent with a structured briefing.

## Why a subagent

A discovery sweep makes 30+ web requests. Doing it in the parent context shifts a huge amount of irrelevant text into your context window, leaving less room for the rest of the run. The subagent does the sweep in its own context and returns a compact JSON summary.

## How to invoke

Use the `Agent` tool with `subagent_type: "tech-scout-scanner"` (the agent definition is in `.claude/agents/tech-scout-scanner.md`).

The prompt body should be the JSON briefing from Phase 1, formatted as text Claude can read. Example:

```
You are running a tech-scout discovery sweep. Briefing:

{
  "time_window": "2026-04-22 to 2026-04-29",
  "focus_area": null,
  "company_summary": "Acme is an AI-powered customer-support platform built on LangGraph + FastAPI + Postgres + Pinecone, with several third-party LLM integrations.",
  "tech_stack_hints": ["Python 3.12", "LangGraph", "LangChain", "FastAPI", "Postgres", "Pinecone", "OpenAI", "Anthropic", "Gemini", "AWS Bedrock"],
  "prior_topics": [
    "Memory layer / Mem0 (2026-04-22 — covered in detail)",
    "AutoHarness paper analysis (2026-03-14 — covered in detail)"
  ],
  "language": "en",
  "depth": "standard"
}

Follow your subagent definition. Return JSON on stdout.
```

If the user has multiple focus areas (e.g., "MCP and evaluation"), set `focus_area` to a comma-separated string and ask the subagent to prefer those categories without ignoring others entirely.

## Validate the output

When the subagent returns, the result should be JSON matching:

```jsonc
{
  "scan_summary": "...",
  "sources_scanned": 25,
  "findings": [
    {
      "id": "F001",
      "title": "...",
      "category": "research-papers",
      "source": { "url": "...", "title": "...", "publication_date": "...", "publisher": "..." },
      "summary": "...",
      "why_relevant": "...",
      "initial_fit": "high"
    },
    ...
  ]
}
```

Run quick sanity checks:

- `findings` length is 20–50. Below 20: ask the subagent to broaden. Above 50: trim weakest before scoring.
- All IDs match `^F\d{3}$` and are unique.
- All `source.url` values are non-empty and look real (have a TLD).
- All `category` values are in the valid enum list (15 slugs from the subagent definition).
- All `initial_fit` values are canonical English: `high`, `medium`, `low`. The display label for the user (in TR runs) is mapped via the locale spec's `fit_label_map`; do not store localized values in JSON.

If the subagent returns malformed output, fix what you can and re-spawn it with corrective instructions if necessary. Don't manually fabricate findings.

## Persist

Write the validated discovery output to:

```
<state_dir>/discovery-findings.json
```

This is the input to Phase 3. If Phase 3 needs to be re-run later, it can read this file instead of re-spawning the scanner.

## Update audit log

After the file is written, the helper scripts will already log their own audit events. You don't need to emit anything extra.

## Edge cases

- **Subagent times out** — re-spawn with a tighter `focus_area` so it can finish faster.
- **Subagent returns < 10 findings** — broaden by removing `focus_area` and re-running. If still < 10, the week may genuinely be quiet; flag this in the user-facing scan summary at end of Phase 3.
- **All findings are in one category** — re-spawn with explicit instruction to "ensure at least 6 categories represented" and pass the prior categories that were missed.
