# Candidate Display Format (Stage A end)

> The exact rendering rules for the user-facing output at the end of Phase 3. The text is locale-aware: every label below comes from the active locale's `candidate_display_labels` and `score_axis_labels` (loaded via `ts_locale_info.py` in Phase 0). Values that use canonical English keys (e.g., `high`/`medium`/`low` for fit) are mapped through `fit_label_map` for display.

## Order of sections

1. **Scan summary** (3-5 lines)
2. **Score table** (top 8-12)
3. **Detailed candidate cards** (8-12 cards)
4. **Honourable mentions** (3-5 entries)
5. **Selection prompt** — verbatim from `LocaleSpec.selection_prompt`

## 1. Scan summary

3-5 lines, paragraph form. Use the heading from `candidate_display_labels.scan_summary_heading`. Body in the run's language:

```markdown
**<scan_summary_heading>**

This week scanned {N1} primary + {N2} secondary sources, produced {N3} raw findings,
shortlisted top {N4}. Three standout themes: {theme1} ({K1} candidates), {theme2}
({K2} candidates), {theme3} ({K3} candidates). {Notable observation}.

{If prior-week overlap exists: brief note that 2 candidates overlap last week's topic
"<topic>", marked with ⚠️ but with a different angle.}

{If a major category is empty: brief note that {category} is empty this week —
may be seasonal.}
```

The above is the *structure*; produce the actual text in the run's language.

## 2. Score table

```markdown
**<score_table_heading>**

| <columns from score_table_columns> |
|----|--------|---|---|---|------|------|
| F003 | AutoHarness ... | 9 | 7 | 6 | 7.5 | <30-60 char note in run's language> |
| F001 | Mem0 v2 ... | 8 | 9 | 4 | 7.0 | … |
| ... |
```

The score column letters (I/U/A in EN, E/A/U in TR) come from
`candidate_display_labels.score_table_columns`. Sort by `overall` descending.

## 3. Detailed candidate cards (8-12)

For each candidate, render:

```markdown
### F003 — <title>

- **<candidate_card_category>:** research-papers · **<candidate_card_source>:** [arxiv.org/abs/2603.03329](https://arxiv.org/abs/2603.03329) · **<candidate_card_date>:** 2026-02-XX
- **<candidate_card_score>:** <impact_label> 9/10 · <urgency_label> 7/10 · <applicability_label> 6/10 — **<overall_label> 7.5/10**
- **<candidate_card_suggested_depth>:** <localized depth>  · **<candidate_card_phase_b_minutes>:** ~75 min

**<candidate_card_one_sentence>:** <localized one-sentence summary>

**<candidate_card_company_relevance>:** <localized company relevance>

**<candidate_card_risk_note>:** <localized risk note>

**<candidate_card_overlaps>:** <no_overlap label or "<prior topic> — same category, different angle: …">

---
```

Field rules:

- Category: 15 slug from the SourceCategory enum (research-papers, agent-frameworks, …). Display the slug as-is.
- Source line: `[domain](url)` format with the date if known.
- Score line: three axes + overall, axis labels from `score_axis_labels`.
- Suggested depth: canonical key from `candidate.suggested_depth` translated through `candidate_display_labels` (`depth_light`, `depth_standard`, `depth_deep`).
- Phase B time: minutes integer.
- Body fields: copy from the candidate's stored language-specific fields (`one_sentence`, `company_relevance`, `risk_note`).
- Overlaps: `no_overlap` label if `overlaps_with_prior` is null; otherwise the saved string verbatim.

## 4. Honourable mentions

```markdown
**<honourable_mentions_heading>**

- **F0XX — <title>** (score: 6.4/10) — <reason in run's language>
- **F0XY — <title>** (score: 6.0/10) — <reason in run's language>
- ...
```

3-5 entries. Score 6.0+. Reasons in the run's language: diversity (category full), prior-week overlap, marketing/weak, etc.

## 5. Selection prompt (verbatim)

Print `LocaleSpec.selection_prompt` exactly as returned by `ts_locale_info.py`. Do not paraphrase, summarize, or abbreviate; the prompt is calibrated to the run's language.

## After printing

**STOP.** Don't run Phase 4. Don't summarize the user's likely choice.
Don't pre-emptively load the analyzer subagent. Wait for the user's
reply.
