"""English locale specification.

This is the canonical reference for what a locale must provide. New
locales should mirror this structure with localized text.
"""

from __future__ import annotations

from tech_scout.domain.enums import Language, OutputDocSlot
from tech_scout.locales.spec import LocaleDocumentSpec, LocaleSpec

_DOCUMENTS: tuple[LocaleDocumentSpec, ...] = (
    LocaleDocumentSpec(
        slot=OutputDocSlot.EXECUTIVE_SUMMARY,
        filename="00-executive-summary.md",
        template_filename="00-executive-summary.md.j2",
        min_words=250,
        required_section_keywords=(
            "headline",
            "problem",
            "solution",
            "investment",
            "call to action",
        ),
    ),
    LocaleDocumentSpec(
        slot=OutputDocSlot.DETAILED_ANALYSIS,
        filename="01-detailed-analysis.md",
        template_filename="01-detailed-analysis.md.j2",
        min_words=1500,
        required_section_keywords=(
            "executive summary",
            "gap analysis",
            "implementation",
            "cost",
            "risk",
            "roadmap",
            "conclusion",
        ),
    ),
    LocaleDocumentSpec(
        slot=OutputDocSlot.PRESENTATION,
        filename="02-presentation.md",
        template_filename="02-presentation.md.j2",
        min_words=800,
    ),
    LocaleDocumentSpec(
        slot=OutputDocSlot.QUICK_REFERENCE,
        filename="03-quick-reference.md",
        template_filename="03-quick-reference.md.j2",
        min_words=200,
        required_section_keywords=(
            "core concepts",
            "three core messages",
            "closing",
        ),
    ),
    LocaleDocumentSpec(
        slot=OutputDocSlot.DIAGRAMS,
        filename="04-diagrams.md",
        template_filename="04-diagrams.md.j2",
        min_words=100,
    ),
    LocaleDocumentSpec(
        slot=OutputDocSlot.SLACK_SUMMARY,
        filename="05-slack-summary.md",
        template_filename="05-slack-summary.md.j2",
        min_words=100,
    ),
    LocaleDocumentSpec(
        slot=OutputDocSlot.SOURCES,
        filename="06-sources.md",
        template_filename="06-sources.md.j2",
        min_words=100,
    ),
    LocaleDocumentSpec(
        slot=OutputDocSlot.README,
        filename="README.md",
        template_filename="README.md.j2",
        min_words=80,
    ),
)


_SELECTION_PROMPT = """\
🔍 **Stage A complete. Two things from you:**

**1. Which candidate(s) should we go deep on?**
Example replies:
- "Go deep on F003"
- "Run F001 and F005 together"
- "F002, F004, F007 — standard depth for all three"
- "None of these — rerun the scan with this angle: ..."

**2. Depth preference?** (default: the depth from your run parameters)
- light / standard / deep — feel free to override per topic.

Reply and I will start Stage B (Phases 4-6): deep analysis + the 8-document package.
"""


_SELECTION_EXAMPLES: tuple[str, ...] = (
    "Go deep on F003",
    "Run F001 and F005 together",
    "F002, F004, F007 — standard depth for all three",
    "None of these — rerun with focus: agent evaluation",
)


_FINAL_SUMMARY_TEMPLATE = """\
✅ **Research package ready.**

📁 **Location:** `{output_folder}`

📋 **Three core messages:**
{three_messages}

🎯 **If we do exactly one thing this week:**
> {single_action}

📣 **Slack-ready post:**
{slack_snippet}

🔮 **Suggested direction for next week:**
{next_week_pointer}

If anything goes wrong, resume with `/tech-scout-resume {run_id}`.
"""


_CANDIDATE_DISPLAY_LABELS = {
    "scan_summary_heading": "Scan summary",
    "score_table_heading": "Score table",
    "score_table_columns": "ID | Title | I | U | A | Score | Note",
    "candidate_card_category": "Category",
    "candidate_card_source": "Source",
    "candidate_card_date": "Date",
    "candidate_card_score": "Score",
    "candidate_card_one_sentence": "One sentence",
    "candidate_card_company_relevance": "Why it matters here",
    "candidate_card_risk_note": "Note / risk",
    "candidate_card_overlaps": "Overlap with prior runs",
    "candidate_card_suggested_depth": "Suggested depth",
    "candidate_card_phase_b_minutes": "Stage B time",
    "honourable_mentions_heading": "Honourable mentions (didn't make the top)",
    "no_overlap": "none",
    "depth_light": "light",
    "depth_standard": "standard",
    "depth_deep": "deep",
}


_SCORE_AXIS_LABELS = {
    "impact": "Impact",
    "urgency": "Urgency",
    "applicability": "Applicability",
    "overall": "Overall",
}


_FIT_LABEL_MAP = {
    "high": "high",
    "medium": "medium",
    "low": "low",
}


EN_LOCALE = LocaleSpec(
    code="en",
    display_name="English",
    aliases=("english",),
    language=Language.ENGLISH,
    template_subdir="en",
    documents=_DOCUMENTS,
    selection_prompt=_SELECTION_PROMPT,
    selection_examples=_SELECTION_EXAMPLES,
    final_summary_template=_FINAL_SUMMARY_TEMPLATE,
    candidate_display_labels=_CANDIDATE_DISPLAY_LABELS,
    score_axis_labels=_SCORE_AXIS_LABELS,
    fit_label_map=_FIT_LABEL_MAP,
)
