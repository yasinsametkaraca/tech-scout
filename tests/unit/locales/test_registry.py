"""Unit tests for the locale registry and per-locale specs."""

from __future__ import annotations

import pytest

from tech_scout.domain.enums import Language, OutputDocSlot
from tech_scout.domain.exceptions import LocaleNotFoundError
from tech_scout.locales import (
    DEFAULT_LOCALE_CODE,
    LocaleSpec,
    get_locale,
    get_locale_for_language,
    list_locales,
)
from tech_scout.locales.registry import LocaleRegistry


class TestRegistryLookup:
    @pytest.mark.parametrize(
        "lookup",
        ["en", "EN", "english", "ENGLISH", "  en  "],
    )
    def test_english_lookup_via_code_and_alias(self, lookup: str) -> None:
        spec = get_locale(lookup)
        assert spec.code == "en"
        assert spec.language == Language.ENGLISH

    @pytest.mark.parametrize(
        "lookup",
        ["tr", "TR", "turkish", "Turkish"],
    )
    def test_turkish_lookup_via_code_and_alias(self, lookup: str) -> None:
        spec = get_locale(lookup)
        assert spec.code == "tr"
        assert spec.language == Language.TURKISH

    def test_unknown_locale_raises(self) -> None:
        with pytest.raises(LocaleNotFoundError):
            get_locale("klingon")

    def test_default_code_resolves(self) -> None:
        spec = get_locale(DEFAULT_LOCALE_CODE)
        assert spec.code == DEFAULT_LOCALE_CODE

    def test_for_language_resolves(self) -> None:
        assert get_locale_for_language(Language.ENGLISH).code == "en"
        assert get_locale_for_language(Language.TURKISH).code == "tr"

    def test_list_locales_returns_all(self) -> None:
        codes = {s.code for s in list_locales()}
        assert {"en", "tr"}.issubset(codes)


class TestSpecInvariants:
    @pytest.mark.parametrize("locale_code", ["en", "tr"])
    def test_spec_covers_every_slot(self, locale_code: str) -> None:
        spec = get_locale(locale_code)
        slots_seen = [d.slot for d in spec.documents]
        assert slots_seen == OutputDocSlot.in_order()

    @pytest.mark.parametrize("locale_code", ["en", "tr"])
    def test_filenames_unique(self, locale_code: str) -> None:
        spec = get_locale(locale_code)
        filenames = [d.filename for d in spec.documents]
        assert len(set(filenames)) == len(filenames)

    @pytest.mark.parametrize("locale_code", ["en", "tr"])
    def test_template_filenames_end_in_j2(self, locale_code: str) -> None:
        spec = get_locale(locale_code)
        for d in spec.documents:
            assert d.template_filename.endswith(".j2")

    @pytest.mark.parametrize("locale_code", ["en", "tr"])
    def test_filenames_end_in_md(self, locale_code: str) -> None:
        spec = get_locale(locale_code)
        for d in spec.documents:
            assert d.filename.endswith(".md")

    @pytest.mark.parametrize("locale_code", ["en", "tr"])
    def test_required_keywords_lowercase(self, locale_code: str) -> None:
        spec = get_locale(locale_code)
        for d in spec.documents:
            for kw in d.required_section_keywords:
                assert kw == kw.lower()

    @pytest.mark.parametrize("locale_code", ["en", "tr"])
    def test_lookup_helpers(self, locale_code: str) -> None:
        spec = get_locale(locale_code)
        slot = OutputDocSlot.EXECUTIVE_SUMMARY
        doc = spec.document(slot)
        assert spec.filename_for(slot) == doc.filename
        assert str(spec.template_path(slot)) == f"{spec.template_subdir}/{doc.template_filename}"


class TestSpecLanguageContent:
    """English and Turkish must produce distinct, non-empty filenames."""

    def test_filenames_differ_between_locales(self) -> None:
        en = get_locale("en")
        tr = get_locale("tr")
        for slot in OutputDocSlot.in_order():
            if slot == OutputDocSlot.README:
                # README.md is the same in both — that's by design.
                assert en.filename_for(slot) == tr.filename_for(slot) == "README.md"
            else:
                assert en.filename_for(slot) != tr.filename_for(slot), slot.value


class TestRegistryConstructorGuards:
    def test_duplicate_code_rejected(self) -> None:
        en = get_locale("en")
        # Same code twice -> reject
        with pytest.raises(ValueError):
            LocaleRegistry({"en": en, "en2": en})

    def test_key_must_match_code(self) -> None:
        en = get_locale("en")
        with pytest.raises(ValueError):
            LocaleRegistry({"english": en})


class TestSpecMatching:
    def test_matches_handles_aliases(self) -> None:
        en: LocaleSpec = get_locale("en")
        assert en.matches("en")
        assert en.matches("EN")
        assert en.matches("english")
        assert not en.matches("tr")
