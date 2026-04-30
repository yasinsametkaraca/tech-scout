# Output Templates Guide

> What each Jinja2 template under `templates/<locale>/` expects in its render context. Phase 4 uses this to build `<state_dir>/render-context-<slot>.json` per slot. Field names are language-neutral and identical across locales — only prose differs.

## Common context (every slot)

These keys are sourced from run metadata, the analyzer output, or sensible defaults. Include them in **every** context.

```jsonc
{
  "topic_title": "AutoHarness x Acme",
  "generated_date": "2026-04-29",
  "author": "AI Engineering",                  // default if not given
  "company_name": "Acme"                       // null if generic mode
}
```

The values themselves should be in the run's language (e.g., `topic_title` in EN runs uses English wording). Keys are constant.

---

## Slot: `executive_summary`

Single-topic structure. Required context fields beyond common:

```jsonc
{
  "headline_message": "1-2 sentence pitch",
  "problem_description": "2-3 sentences, non-technical",
  "solution_description": "2-3 sentences, non-technical",
  "investment": {
    "summary": "$X / N engineer-weeks",
    "engineer_weeks": "4-6"
  },
  "roi": {
    "payback_period": "6-9 months",
    "annual_value": "~$X"
  },
  "risk_level": "Low|Medium|High",
  "plan_phases": [
    { "timeframe": "0-4 weeks", "description": "..." },
    { "timeframe": "1-3 months", "description": "..." },
    { "timeframe": "3-6 months", "description": "..." }
  ],
  "decisions_needed": ["...", "...", "..."],
  "call_to_action": "If we do exactly one thing this week..."
}
```

For multi-topic packages, the headline_message and call_to_action become combined; problem/solution/plan still single (the umbrella).

---

## Slot: `detailed_analysis`

The big one. Required:

```jsonc
{
  "primary_source": { "url": "...", "title": "...", "publication_date": "...", "publisher": "..." },
  "executive_summary": { "what": "...", "relevance": "...", "thesis": "..." },
  "deep_dive": {
    "problem": "...",
    "architecture": "...",
    "code_example": null,        // optional string
    "code_language": "python",
    "code_explanation": "...",
    "results_table": [{ "metric": "...", "value": "..." }],   // optional
    "results": "...",            // fallback prose if no table
    "limitations": ["..."]
  },
  "company_state": {
    "overview": "...",
    "relevant_modules": [{ "name": "...", "description": "..." }],
    "existing_mechanisms": [{ "name": "...", "location": "src/...", "description": "..." }],
    "strengths_weaknesses": [{ "strength": "...", "weakness": "..." }]
  },
  "gap_analysis": [{ "concept": "...", "local_equivalent": "...", "current": "...", "target": "..." }],
  "implementation_layers": [
    {
      "name": "...",
      "what": "...",
      "why": "...",
      "design": "...",
      "code_example": null,
      "code_language": "python",
      "impacts": ["..."],
      "effort": "..."
    }
  ],
  "cost_benefit": {
    "investment_items": [{ "label": "...", "value": "..." }],
    "return_items": [{ "label": "...", "value": "..." }],
    "break_even_analysis": "...",
    "enterprise_value": [{ "dimension": "...", "description": "..." }]
  },
  "risks": [{ "name": "...", "level": "...", "description": "...", "mitigation": "..." }],
  "skeptic_questions": [{ "question": "...", "answer": "..." }],
  "roadmap": [
    {
      "title": "...",
      "timeframe": "...",
      "scope": ["..."],
      "acceptance_criteria": ["..."],
      "effort": "..."
    }
  ],
  "conclusion": {
    "thesis": "...",
    "why_now": ["..."],
    "cautions": ["..."],
    "open_questions": ["..."]
  },
  "secondary_sources": [...],
  "codebase_refs": [...],
  "key_quotes": [{ "text": "...", "attribution": "..." }]
}
```

For multi-topic, repeat the body sections (`executive_summary` through `conclusion`) once per topic.

---

## Slot: `presentation`

```jsonc
{
  "talk_duration_minutes": 15,
  "qa_duration_minutes": 10,
  "slides": [
    {
      "title": "Cover",
      "visual": "Title + subtitle + name/date",
      "speech": "30-second speaking notes",
      "speaking_seconds": 30,
      "note": "Start slow, stay calm"            // optional
    }
    // 18-22 slides total
  ],
  "qa_pairs": [{ "question": "...", "answer": "..." }],          // 10-15 pairs
  "time_management": [{ "minute": "0-1.5", "slide": "1-3", "topic": "Opening" }],
  "style_tips": ["..."],
  "closing_line": "If we do one thing in the next 3 months..."
}
```

---

## Slot: `quick_reference`

```jsonc
{
  "core_concepts": [{ "name": "...", "one_liner": "...", "note": "..." }],
  "key_numbers": ["..."],
  "top_gaps": [{ "label": "...", "description": "..." }],          // 3 items
  "top_recommendations": [{ "title": "...", "effort": "...", "impact": "..." }],   // 3 items
  "top_dangers": [{ "title": "...", "description": "..." }],       // 3 items
  "three_messages": ["...", "...", "..."],
  "top_questions": [{ "question": "...", "answer": "..." }],       // 5 items
  "closing_line": "..."
}
```

---

## Slot: `diagrams`

```jsonc
{
  "diagrams": [
    {
      "title": "Current architecture",
      "type": "mermaid",        // or "ascii"
      "content": "graph TD\n  A --> B",
      "slide_recommendation": "Slide 6",
      "caption": "..."
    }
    // 5-8 diagrams typical
  ],
  "style_palette": [
    { "name": "Primary", "hex": "#1F4E79", "use": "headings" }
  ],
  "typography": "Inter, heading 32-44pt, body 18-22pt"
}
```

If the analyzer doesn't supply diagrams, fill `diagrams` with at least 2: one architecture diagram, one before/after comparison.

---

## Slot: `slack_summary`

```jsonc
{
  "slack_channel": "#engineering, #ai-research",
  "slack_headline": "...",
  "slack_intro": "1-2 sentences",
  "tldr": "1 sentence",
  "what_caught_eye": "2-3 sentences",
  "what_it_means_for_us": [
    { "kind": "pro", "text": "..." },          // ✅
    { "kind": "con", "text": "..." },          // ⚠️
    { "kind": "info", "text": "..." }          // 💡
  ],
  "slack_numbers": [
    { "icon": "📊", "text": "..." }
  ],
  "detailed_analysis_size": "~30 min read",
  "detailed_analysis_pointer": "reply in thread",
  "topic_tag": "mcp"                           // for hashtag at end
}
```

The slack slot can be rendered in a different locale than the rest of the package (`--slack-locale-code`), so its body text matches the chosen slack language even if the rest of the package uses a different one.

---

## Slot: `sources`

```jsonc
{
  "primary_sources": [
    { "title": "...", "url": "...", "publication_date": "...", "why": "..." }
  ],
  "secondary_sources": [
    { "title": "...", "url": "...", "publication_date": "...", "position": "...", "argument": "..." }
  ],
  "contrarian_sources": [
    { "title": "...", "url": "...", "publication_date": "...", "argument": "..." }
  ],
  "codebase_refs": [{ "path": "src/...", "line": 42, "note": "..." }],
  "related_prior_runs": [{ "date": "2026-04-22", "title": "...", "relationship": "..." }],
  "further_reading": [{ "title": "...", "url": "...", "why": "..." }]
}
```

`primary_sources` always required (≥1 entry). Others can be empty arrays — the template renders graceful fallbacks.

---

## Slot: `readme`

```jsonc
{
  "week_label": "2026-W17",
  "category": "agent-frameworks",
  "overall_score": 8.2,
  "time_horizon": "3 months",
  "single_action": "...",
  "three_messages": ["...", "...", "..."],
  "next_steps": ["..."],
  "run_metadata": {
    "run_id": "2026-04-29-abc123",
    "scan_window": "2026-04-22 to 2026-04-29",
    "sources_scanned": 33,
    "candidate_count": 11,
    "selected_ids": ["F003"],
    "depth": "deep"
  }
}
```

---

## Building contexts efficiently

Most fields come straight from analyzer output (`<state_dir>/analysis-<F-ID>.json`). The mapping:

- `analyzer.executive_summary` → `detailed_analysis` slot's `executive_summary`
- `analyzer.executive_brief` → `executive_summary` slot's top-level fields
- `analyzer.presentation_assets` → `presentation` slot's `slides` + `qa_pairs` + `style_tips`
- `analyzer.quick_reference` → `quick_reference` slot (1:1 mapping)
- `analyzer.diagrams` → `diagrams` slot's `diagrams`
- `analyzer.slack` → `slack_summary` slot's `slack_*` fields
- `analyzer.primary_source` + `secondary_sources` + `contrarian_sources` → `sources` slot
- `analyzer.three_messages`, `single_action`, `next_steps` → `readme` slot

Build the context dicts by **copying analyzer fields**, then adding `topic_title`, `generated_date`, `author`, `company_name`, `run_metadata`. Don't paraphrase analyzer content into different shapes — that loses fidelity.
