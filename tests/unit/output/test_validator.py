"""Unit tests for the package validator."""

from __future__ import annotations

from pathlib import Path

import pytest

from tech_scout.domain.exceptions import ValidationError
from tech_scout.locales import get_locale
from tech_scout.output import PackageValidator


def _write_minimal_english_package(target: Path) -> None:
    """Write a small but structurally valid English package."""
    target.mkdir(parents=True, exist_ok=True)

    (target / "00-executive-summary.md").write_text(
        "# Executive Summary — Test\n\n"
        "## Headline Message\n\nOne sentence.\n\n"
        "## Problem\n\nProblem here.\n\n"
        "## Solution\n\nSolution here.\n\n"
        "## Investment\n\nLow.\n\n"
        "## Call to Action\n\nDo this.\n\n" + "x " * 250,
        encoding="utf-8",
    )

    (target / "01-detailed-analysis.md").write_text(
        "# Detailed Analysis\n\n## Executive Summary\n\nSummary.\n\n"
        "## Gap Analysis\n\nGap.\n\n## Implementation Layers\n\nLayers.\n\n"
        "## Cost-Benefit Analysis\n\nCost.\n\n## Risk Analysis\n\nRisk.\n\n"
        "## Implementation Roadmap\n\nRoadmap.\n\n"
        "## Conclusion\n\nConclusion.\n\n" + "word " * 1500,
        encoding="utf-8",
    )

    (target / "02-presentation.md").write_text(
        "# Presentation\n\n## SLIDE 1: Cover\n\n" + "speech " * 800,
        encoding="utf-8",
    )

    (target / "03-quick-reference.md").write_text(
        "# Quick Reference\n\n## Core Concepts\n\nConcepts.\n\n"
        "## Three Core Messages\n\nMessages.\n\n## Closing\n\nEnd.\n\n" + "x " * 250,
        encoding="utf-8",
    )

    (target / "04-diagrams.md").write_text(
        "# Diagrams\n\n```mermaid\ngraph TD\n  A --> B\n```\n" + "x " * 100,
        encoding="utf-8",
    )

    (target / "05-slack-summary.md").write_text(
        "# Slack\n\nMessage here.\n" + "x " * 100,
        encoding="utf-8",
    )

    (target / "06-sources.md").write_text(
        "# Sources\n\n[link](https://example.com)\n" + "x " * 100,
        encoding="utf-8",
    )

    (target / "README.md").write_text(
        "# README\n\nPackage contents.\n" + "x " * 80,
        encoding="utf-8",
    )


def _write_minimal_turkish_package(target: Path) -> None:
    """Write a small but structurally valid Turkish package."""
    target.mkdir(parents=True, exist_ok=True)

    (target / "00-yonetici-ozeti.md").write_text(
        "# Yönetici Özeti — Test\n\n"
        "## Tek Cümlede Mesaj\n\nBir cümle.\n\n"
        "## Sorun\n\nProblem var.\n\n"
        "## Çözüm\n\nÇözüm bu.\n\n"
        "## Yatırım\n\nDüşük.\n\n"
        "## Eylem Çağrısı\n\nBunu yap.\n\n" + "x " * 250,
        encoding="utf-8",
    )

    (target / "01-detayli-analiz.md").write_text(
        "# Detaylı Analiz\n\n## Executive Summary\n\nÖzet.\n\n"
        "## Gap Analizi\n\nGap.\n\n## Uygulama Katmanları\n\nKatmanlar.\n\n"
        "## Maliyet\n\nMaliyet.\n\n## Risk\n\nRisk.\n\n## Yol Haritası\n\nHarita.\n\n"
        "## Sonuç\n\nSonuç.\n\n" + "kelime " * 1500,
        encoding="utf-8",
    )

    (target / "02-sunum.md").write_text(
        "# Sunum\n\n## SLAYT 1: Kapak\n\n" + "metin " * 800,
        encoding="utf-8",
    )

    (target / "03-hizli-referans.md").write_text(
        "# Hızlı Referans\n\n## Ana Kavramlar\n\nKavramlar.\n\n"
        "## Üç Temel Mesaj\n\nMesajlar.\n\n## Kapanış\n\nSon.\n\n" + "x " * 250,
        encoding="utf-8",
    )

    (target / "04-gorsel-diyagramlar.md").write_text(
        "# Diyagramlar\n\n```mermaid\ngraph TD\n  A --> B\n```\n" + "x " * 100,
        encoding="utf-8",
    )

    (target / "05-slack-ozeti.md").write_text(
        "# Slack\n\nMesaj burada.\n" + "x " * 100,
        encoding="utf-8",
    )

    (target / "06-kaynaklar.md").write_text(
        "# Kaynaklar\n\n[link](https://example.com)\n" + "x " * 100,
        encoding="utf-8",
    )

    (target / "README.md").write_text(
        "# README\n\nPaket içeriği.\n" + "x " * 80,
        encoding="utf-8",
    )


class TestPackageValidatorEnglish:
    def test_complete_package_passes(self, tmp_path: Path) -> None:
        _write_minimal_english_package(tmp_path)
        report = PackageValidator(locale=get_locale("en")).validate(tmp_path)
        assert report.passed
        assert report.error_count == 0
        assert len(report.documents_present) == 8
        assert report.documents_missing == ()

    def test_missing_documents_fail(self, tmp_path: Path) -> None:
        # Only write 3 of 8
        (tmp_path / "00-executive-summary.md").write_text("# x\n", encoding="utf-8")
        (tmp_path / "01-detailed-analysis.md").write_text("# x\n", encoding="utf-8")
        (tmp_path / "06-sources.md").write_text("# x\n", encoding="utf-8")
        report = PackageValidator(locale=get_locale("en")).validate(tmp_path)
        assert not report.passed
        assert len(report.documents_missing) == 5

    def test_unrendered_jinja_caught(self, tmp_path: Path) -> None:
        _write_minimal_english_package(tmp_path)
        (tmp_path / "00-executive-summary.md").write_text(
            "# Test\n\nHello {{ name }}\n",
            encoding="utf-8",
        )
        report = PackageValidator(locale=get_locale("en")).validate(tmp_path)
        errors = [i for i in report.issues if i.severity == "error"]
        assert any("Unrendered Jinja2" in i.message for i in errors)
        assert not report.passed

    def test_no_heading_caught(self, tmp_path: Path) -> None:
        _write_minimal_english_package(tmp_path)
        (tmp_path / "00-executive-summary.md").write_text("just text", encoding="utf-8")
        report = PackageValidator(locale=get_locale("en")).validate(tmp_path)
        errors = [i for i in report.issues if i.severity == "error"]
        assert any("No markdown heading" in i.message for i in errors)
        assert not report.passed

    def test_short_doc_warns(self, tmp_path: Path) -> None:
        _write_minimal_english_package(tmp_path)
        (tmp_path / "01-detailed-analysis.md").write_text(
            "# Detailed Analysis\n## Executive Summary\nShort.\n",
            encoding="utf-8",
        )
        report = PackageValidator(locale=get_locale("en")).validate(tmp_path)
        warnings = [i for i in report.issues if i.severity == "warning"]
        assert any("shorter than expected" in i.message for i in warnings)

    def test_nonexistent_path_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ValidationError):
            PackageValidator(locale=get_locale("en")).validate(tmp_path / "missing")

    def test_path_not_dir_raises(self, tmp_path: Path) -> None:
        f = tmp_path / "file"
        f.write_text("x")
        with pytest.raises(ValidationError):
            PackageValidator(locale=get_locale("en")).validate(f)


class TestPackageValidatorTurkish:
    def test_complete_package_passes(self, tmp_path: Path) -> None:
        _write_minimal_turkish_package(tmp_path)
        report = PackageValidator(locale=get_locale("tr")).validate(tmp_path)
        assert report.passed
        assert len(report.documents_present) == 8

    def test_english_filenames_against_turkish_locale_fails(self, tmp_path: Path) -> None:
        _write_minimal_english_package(tmp_path)
        report = PackageValidator(locale=get_locale("tr")).validate(tmp_path)
        # Turkish locale expects Turkish filenames; English ones look "missing".
        assert not report.passed
        assert len(report.documents_missing) >= 1


class TestSlackLocaleOverride:
    def test_english_package_with_turkish_slack_validates(self, tmp_path: Path) -> None:
        _write_minimal_english_package(tmp_path)
        # Replace the English slack file with the Turkish one to simulate override.
        (tmp_path / "05-slack-summary.md").unlink()
        (tmp_path / "05-slack-ozeti.md").write_text(
            "# Slack\n\nMesaj.\n" + "x " * 100,
            encoding="utf-8",
        )
        report = PackageValidator(
            locale=get_locale("en"),
            slack_locale=get_locale("tr"),
        ).validate(tmp_path)
        assert report.passed
