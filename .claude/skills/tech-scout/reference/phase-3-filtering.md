# Phase 3 — Filtering & Shortlist (Stage A end)

> **Goal:** Score the raw findings, pick a diverse top-8-12 shortlist, present it to the user, and **stop**. The user picks; you don't.

## Step 1 — Score every finding

For each finding from Phase 2, rate three axes (1-10 integers):

- **Impact** — if integrated, how much measurable value to the company?
- **Urgency** — what is lost by not acting now (competitive position, technical debt)?
- **Applicability** — how easily does it fit the existing stack/architecture?

Compute:

```
overall = 0.4 * impact + 0.3 * urgency + 0.3 * applicability
```

Round overall to one decimal. The arithmetic is in
[`CandidateScore`](../../../../src/tech_scout/domain/models.py); your scores
will be validated against this formula when the helper writes them.

If `company_summary` is null (general mode), substitute "for any AI engineering team" — Applicability becomes "fits the most common stack".

## Step 2 — Build the shortlist (8-12 candidates)

Diversity matters more than score for a shortlist of 12:

- Across the **15 source categories**, aim for at least 6 represented.
- No two top candidates from the exact same source publisher.
- Skip any finding whose topic *strongly overlaps* an entry in `prior_topics`. If borderline, keep it but mark `overlaps_with_prior` in the candidate metadata.

Sort by `overall` descending; then iterate, taking the next finding only if it doesn't violate the diversity rules. Continue until you have 8-12 picks (10 is the sweet spot).

## Step 3 — Build the candidate metadata

For each pick, fill in:

```jsonc
{
  "id": "F003",
  "title": "AutoHarness: Improving LLM Agents by Auto-Synthesizing Code Harness",
  "category": "research-papers",
  "source": {
    "url": "https://arxiv.org/abs/2603.03329",
    "title": "AutoHarness: Improving LLM Agents by Auto-Synthesizing Code Harness",
    "publication_date": "2026-02-XX",
    "publisher": "arXiv (Google DeepMind)"
  },
  "score": {
    "impact": 9,
    "urgency": 7,
    "applicability": 6,
    "overall": 7.5
  },
  "one_sentence": "<one technical-but-readable sentence in the run's language>",
  "company_relevance": "<2-4 sentences in the run's language about how it intersects the company's stack/modules>",
  "risk_note": "<one sentence in the run's language: maturity, lock-in, hyperscaler risk, etc.>",
  "overlaps_with_prior": null,
  "suggested_depth": "deep",
  "estimated_phase_b_minutes": 75
}
```

Field rules:

- `one_sentence`: 1 sentence, 200-400 characters, in the run's language.
- `company_relevance`: 2-4 sentences in the run's language. Lean on Phase 1 output. If no company, use "For an AI engineering team" framing.
- `risk_note`: 1 sentence on maturity / lock-in / hyperscaler etc., in the run's language.
- `overlaps_with_prior`: `null` if no overlap; otherwise `"<prior topic name> — same category, different angle: <angle>"` in the run's language.
- `suggested_depth`: deep technical topic → `"deep"`, product launch → `"light"`, most → `"standard"`.
- `estimated_phase_b_minutes`: light=20, standard=45, deep=75 base. Add 10-30 min depending on scope.

## Step 4 — Honourable mentions (3-5 entries)

From findings that didn't make the top-12 but scored ≥ 6.0, list 3-5 with one-line elimination reasons. Use the original `Finding` schema (no scoring expansion needed).

## Step 5 — Build the CandidateList JSON

Compose a single JSON file:

```jsonc
{
  "candidates": [ /* 8-12 Candidate objects from Step 3 */ ],
  "honourable_mentions": [ /* 3-5 Finding objects from Step 4 */ ],
  "scan_summary": "<3-5 line scan summary in the run's language>",
  "sources_scanned": 33,
  "raw_findings_count": 27
}
```

Write this to `<state_dir>/candidates-input.json`. Then call:

```bash
python scripts/ts_save_candidates.py \
    --run-id <run-id> \
    --output-folder "<output_folder>" \
    --candidates-file "<state_dir>/candidates-input.json"
```

The helper validates the schema (CandidateList requires unique IDs, score consistency, etc.) and writes the canonical `<state_dir>/candidates.json`.

## Step 6 — Render the user-facing display

See `reference/candidate-format.md` for the format. The display has:

1. **Scan summary block** (3-5 lines)
2. **Score table** (top 8-12, columns: ID, Title, I, U, A, Score, Note)
3. **Detailed candidate cards** (8-12 cards, formatted per `candidate-format.md`)
4. **Honourable mentions** (3-5 single-line entries)
5. **Selection prompt** — print the `selection_prompt` field from the active locale (loaded in Phase 0 via `ts_locale_info.py`) **verbatim**.

All headers, labels, and column names come from the active locale's `candidate_display_labels` and `score_axis_labels`. Do not invent locale text or transliterate; if a label is missing from the spec, log a warning and use the slot key as a fallback so the issue is visible.

## Step 7 — STOP

Print the display, then **stop**. Do not run Phase 4. Do not pre-emptively pick. Do not say "I'll continue with the highest-scored one" — that defeats the entire two-stage design.

If the user says "go on" / "continue" without specifying an ID, ask one clarifying question in the run's language: "Which candidate (e.g., F003) should we go deep on?". Don't guess.

## Edge cases

- **Fewer than 8 strong candidates** — present what you have (5-7) and explicitly tell the user the field was thin this week. They may pick one or ask for a re-scan with broader criteria.
- **More than 12 strong candidates** — trim to 12 by enforcing diversity rules harder.
- **All candidates strongly overlap prior topics** — flag this loudly in `scan_summary` and ask the user whether to broaden.
