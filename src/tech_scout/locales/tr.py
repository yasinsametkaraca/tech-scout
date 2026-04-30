"""Turkish locale specification."""

from __future__ import annotations

from tech_scout.domain.enums import Language, OutputDocSlot
from tech_scout.locales.spec import LocaleDocumentSpec, LocaleSpec

_DOCUMENTS: tuple[LocaleDocumentSpec, ...] = (
    LocaleDocumentSpec(
        slot=OutputDocSlot.EXECUTIVE_SUMMARY,
        filename="00-yonetici-ozeti.md",
        template_filename="00-yonetici-ozeti.md.j2",
        min_words=250,
        required_section_keywords=(
            "tek cümlede mesaj",
            "sorun",
            "çözüm",
            "yatırım",
            "eylem çağrısı",
        ),
    ),
    LocaleDocumentSpec(
        slot=OutputDocSlot.DETAILED_ANALYSIS,
        filename="01-detayli-analiz.md",
        template_filename="01-detayli-analiz.md.j2",
        min_words=1500,
        required_section_keywords=(
            "executive summary",
            "gap analizi",
            "uygulama katmanları",
            "maliyet",
            "risk",
            "yol haritası",
            "sonuç",
        ),
    ),
    LocaleDocumentSpec(
        slot=OutputDocSlot.PRESENTATION,
        filename="02-sunum.md",
        template_filename="02-sunum.md.j2",
        min_words=800,
    ),
    LocaleDocumentSpec(
        slot=OutputDocSlot.QUICK_REFERENCE,
        filename="03-hizli-referans.md",
        template_filename="03-hizli-referans.md.j2",
        min_words=200,
        required_section_keywords=(
            "ana kavramlar",
            "üç temel mesaj",
            "kapanış",
        ),
    ),
    LocaleDocumentSpec(
        slot=OutputDocSlot.DIAGRAMS,
        filename="04-gorsel-diyagramlar.md",
        template_filename="04-gorsel-diyagramlar.md.j2",
        min_words=100,
    ),
    LocaleDocumentSpec(
        slot=OutputDocSlot.SLACK_SUMMARY,
        filename="05-slack-ozeti.md",
        template_filename="05-slack-ozeti.md.j2",
        min_words=100,
    ),
    LocaleDocumentSpec(
        slot=OutputDocSlot.SOURCES,
        filename="06-kaynaklar.md",
        template_filename="06-kaynaklar.md.j2",
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
🔍 **Aşama A tamamlandı. Senden iki şey rica ediyorum:**

**1. Hangi aday(lar)la devam edelim?**
Örnek cevaplar:
- "F003 ile derinlemesine git"
- "F001 ve F005'i birlikte işle"
- "F002, F004, F007 — üçü için standart derinlik"
- "Hiçbiri uygun değil, taramayı şu açıyla tekrar et: ..."

**2. Derinlik tercihin?** (varsayılan: parametredeki derinlik)
- hafif / standart / derin — istersen seçtiğin konu için override edebilirsin.

Yanıtını verince Aşama B'yi (FAZ 4-6) başlatacağım: derin analiz + 8 dosyalık sunum paketi.
"""


_SELECTION_EXAMPLES: tuple[str, ...] = (
    "F003 ile derinlemesine git",
    "F001 ve F005'i birlikte işle",
    "F002, F004, F007 — üçü için standart derinlik",
    "Hiçbiri uygun değil, taramayı şu açıyla tekrar et: agent evaluation",
)


_FINAL_SUMMARY_TEMPLATE = """\
✅ **Araştırma paketi hazır.**

📁 **Konum:** `{output_folder}`

📋 **Üç temel mesaj:**
{three_messages}

🎯 **Bu hafta tek bir şey yapacaksak:**
> {single_action}

📣 **Slack için hazır:**
{slack_snippet}

🔮 **Önümüzdeki haftaya öneri:**
{next_week_pointer}

Sorun olursa `/tech-scout-resume {run_id}` ile devam edebilirsin.
"""


_CANDIDATE_DISPLAY_LABELS = {
    "scan_summary_heading": "Tarama özeti",
    "score_table_heading": "Skor tablosu",
    "score_table_columns": "ID | Başlık | E | A | U | Skor | Notu",
    "candidate_card_category": "Kategori",
    "candidate_card_source": "Kaynak",
    "candidate_card_date": "Tarih",
    "candidate_card_score": "Skor",
    "candidate_card_one_sentence": "Tek cümlede",
    "candidate_card_company_relevance": "Şirket için",
    "candidate_card_risk_note": "Not / risk",
    "candidate_card_overlaps": "Önceki haftalarla",
    "candidate_card_suggested_depth": "Önerilen derinlik",
    "candidate_card_phase_b_minutes": "Aşama B süresi",
    "honourable_mentions_heading": "Onurlu zikir (TOP'a giremeyenler)",
    "no_overlap": "yok",
    "depth_light": "hafif",
    "depth_standard": "standart",
    "depth_deep": "derin",
}


_SCORE_AXIS_LABELS = {
    "impact": "Etki",
    "urgency": "Aciliyet",
    "applicability": "Uygulanabilirlik",
    "overall": "Genel",
}


_FIT_LABEL_MAP = {
    "high": "yüksek",
    "medium": "orta",
    "low": "düşük",
}


TR_LOCALE = LocaleSpec(
    code="tr",
    display_name="Türkçe",
    aliases=("turkish",),
    language=Language.TURKISH,
    template_subdir="tr",
    documents=_DOCUMENTS,
    selection_prompt=_SELECTION_PROMPT,
    selection_examples=_SELECTION_EXAMPLES,
    final_summary_template=_FINAL_SUMMARY_TEMPLATE,
    candidate_display_labels=_CANDIDATE_DISPLAY_LABELS,
    score_axis_labels=_SCORE_AXIS_LABELS,
    fit_label_map=_FIT_LABEL_MAP,
)
