# Phase 1 — Context

> **Goal:** Build a tech-stack profile and architecture summary so Phase 2's discovery sweep can target what's relevant. Three branches based on inputs.

## Branch A — Codebase path is provided

Bash:

```bash
python scripts/ts_scan_codebase.py "<codebase_path>" \
    --output "<state_dir>/codebase-profile.json"
```

Parse the JSON envelope. The `data.profile` field is the full
[`CodebaseProfile`](../../../../src/tech_scout/domain/models.py) model.

The `summary` field is a quick overview:

```json
{
  "entry_count": 47,
  "manifest_count": 8,
  "primary_languages": ["Python", "JavaScript/TypeScript"],
  "has_multi_agent": true,
  "pattern": "microservices"
}
```

Use this when briefing Phase 2's scanner — pass the languages, agent
frameworks, and integrations into the briefing payload.

If the script's `data.profile.entries` is empty (no manifests recognized),
fall back to Branch B (treat as if no codebase, just a name).

## Branch B — Only company name / description / website provided

If `company_website` is set, **start there**: `WebFetch` the homepage,
plus the most informative subpages (`/about`, `/engineering`, `/blog`,
`/careers`, `/product`). The team's own page is the highest-signal
source on what they build.

Then supplement with `WebSearch` (3-5 queries):

```
"<company_name> tech stack"
"<company_name> engineering blog"
"<company_name> product"
"<company_name> hiring engineer"   # job postings often leak the stack
"<company_name> case study"
```

`WebFetch` the top 1-2 results for each query, but don't go deeper than
3-4 pages total beyond the website itself. Build a tentative profile:

```json
{
  "primary_languages_guess": ["Python", "TypeScript"],
  "agent_frameworks_guess": ["LangChain"],
  "domain": "hiring tech",
  "confidence": "low"
}
```

Be honest about confidence. Mark every claim as a guess unless you have
direct citation. Phase 2's scanner uses this as a hint, not as truth.

## Branch C — Neither codebase nor company

"General best-of-week mode." Skip codebase scan entirely. Phase 2's
scanner runs without company hints — it returns the most generally
useful AI/software news of the week. No stack profile is persisted.

## Output

In all branches, optionally write:

```
<state_dir>/codebase-profile.json   # Branch A only
<state_dir>/company-context.json    # Branches A and B
```

`company-context.json` schema:

```jsonc
{
  "company_name": "...",
  "company_description": "...",
  "tech_stack_summary": "1 paragraph plain-English description",
  "stack_categories": [
    { "kind": "language", "items": ["Python 3.12"] },
    { "kind": "agent-framework", "items": ["LangGraph 1.0"] }
  ],
  "domain": "...",
  "weaknesses_observed": ["..."],
  "strengths_observed": ["..."],
  "confidence": "high|medium|low",
  "branch": "A|B|C"
}
```

This file is the briefing artifact for Phase 2's subagent.

## What to Pass to Phase 2

Build the discovery briefing as:

```jsonc
{
  "time_window": "<start> to <end>",
  "focus_area": "...",                   // user-supplied or null
  "company_summary": "...",              // 1-paragraph from Phase 1
  "tech_stack_hints": [                  // flattened list
    "Python 3.12",
    "LangGraph",
    "FastAPI",
    "MongoDB",
    "Pinecone"
  ],
  "prior_topics": [                      // from Phase 0
    "Memory layer for agents (last week)",
    "AutoHarness paper analysis (2 weeks ago)"
  ],
  "language": "en",                      // canonical 2-letter code from Phase 0
  "depth": "standard"
}
```

Persist this briefing to `<state_dir>/discovery-briefing.json` in case
you need to re-run Phase 2.
