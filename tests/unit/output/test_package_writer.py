"""Unit tests for the package writer."""

from __future__ import annotations

from pathlib import Path

import pytest
from jinja2 import DictLoader

from tech_scout.domain.enums import OutputDocSlot
from tech_scout.domain.exceptions import TemplateRenderError
from tech_scout.locales import get_locale
from tech_scout.output import PackageWriter, TemplateRenderer


def _build_renderer_for_locales() -> TemplateRenderer:
    """Build a renderer that has a one-line template for each slot in en + tr."""
    templates: dict[str, str] = {}
    for code in ("en", "tr"):
        spec = get_locale(code)
        for slot in OutputDocSlot.in_order():
            doc = spec.document(slot)
            templates[f"{spec.template_subdir}/{doc.template_filename}"] = (
                f"# {{{{ title }}}}\n{spec.code}/{doc.filename}\n"
            )
    return TemplateRenderer(loader=DictLoader(templates))


def test_write_doc_creates_file_for_english(tmp_path: Path) -> None:
    en = get_locale("en")
    renderer = _build_renderer_for_locales()
    writer = PackageWriter(renderer=renderer, output_folder=tmp_path, locale=en)
    target = writer.write_doc(OutputDocSlot.EXECUTIVE_SUMMARY, {"title": "Demo"})
    assert target == tmp_path / "00-executive-summary.md"
    assert target.read_text(encoding="utf-8").startswith("# Demo")


def test_write_doc_creates_file_for_turkish(tmp_path: Path) -> None:
    tr = get_locale("tr")
    renderer = _build_renderer_for_locales()
    writer = PackageWriter(renderer=renderer, output_folder=tmp_path, locale=tr)
    target = writer.write_doc(OutputDocSlot.EXECUTIVE_SUMMARY, {"title": "Demo"})
    assert target == tmp_path / "00-yonetici-ozeti.md"
    assert target.read_text(encoding="utf-8").startswith("# Demo")


def test_write_all_creates_eight_files_per_locale(tmp_path: Path) -> None:
    en = get_locale("en")
    renderer = _build_renderer_for_locales()
    writer = PackageWriter(renderer=renderer, output_folder=tmp_path, locale=en)
    contexts = {slot: {"title": slot.value} for slot in OutputDocSlot}
    written = writer.write_all(contexts)
    assert len(written) == 8
    for path in written:
        assert path.is_file()


def test_write_all_missing_context_raises(tmp_path: Path) -> None:
    en = get_locale("en")
    renderer = _build_renderer_for_locales()
    writer = PackageWriter(renderer=renderer, output_folder=tmp_path, locale=en)
    contexts = {
        slot: {"title": "x"} for slot in OutputDocSlot if slot != OutputDocSlot.PRESENTATION
    }
    with pytest.raises(TemplateRenderError):
        writer.write_all(contexts)


def test_slack_locale_overrides_only_slack_slot(tmp_path: Path) -> None:
    en = get_locale("en")
    tr = get_locale("tr")
    renderer = _build_renderer_for_locales()
    writer = PackageWriter(
        renderer=renderer,
        output_folder=tmp_path,
        locale=en,
        slack_locale=tr,
    )
    writer.write_doc(OutputDocSlot.EXECUTIVE_SUMMARY, {"title": "x"})
    writer.write_doc(OutputDocSlot.SLACK_SUMMARY, {"title": "y"})
    # English package, Turkish slack
    assert (tmp_path / "00-executive-summary.md").is_file()
    assert (tmp_path / "05-slack-ozeti.md").is_file()
    assert not (tmp_path / "05-slack-summary.md").exists()


def test_list_existing_returns_empty_when_folder_missing(tmp_path: Path) -> None:
    en = get_locale("en")
    renderer = _build_renderer_for_locales()
    writer = PackageWriter(renderer=renderer, output_folder=tmp_path / "missing", locale=en)
    assert writer.list_existing() == []


def test_list_existing_finds_written_files(tmp_path: Path) -> None:
    en = get_locale("en")
    renderer = _build_renderer_for_locales()
    writer = PackageWriter(renderer=renderer, output_folder=tmp_path, locale=en)
    writer.write_doc(OutputDocSlot.EXECUTIVE_SUMMARY, {"title": "x"})
    writer.write_doc(OutputDocSlot.SLACK_SUMMARY, {"title": "y"})
    existing = writer.list_existing()
    names = {p.name for p in existing}
    assert "00-executive-summary.md" in names
    assert "05-slack-summary.md" in names
    assert "01-detailed-analysis.md" not in names


def test_output_folder_property(tmp_path: Path) -> None:
    en = get_locale("en")
    renderer = _build_renderer_for_locales()
    writer = PackageWriter(renderer=renderer, output_folder=tmp_path, locale=en)
    assert writer.output_folder == tmp_path
    assert writer.locale.code == "en"
    assert writer.slack_locale.code == "en"
