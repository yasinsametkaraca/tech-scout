"""Unit tests for the package-data template lookup."""

from __future__ import annotations

from pathlib import Path

from tech_scout.output.template_assets import (
    is_packaged_templates_writable_check,
    packaged_templates_root,
)


class TestPackagedTemplatesRoot:
    def test_returns_existing_directory(self) -> None:
        root = packaged_templates_root()
        assert isinstance(root, Path)
        assert root.is_dir()

    def test_contains_locale_subdirs(self) -> None:
        root = packaged_templates_root()
        en = root / "en"
        tr = root / "tr"
        assert en.is_dir()
        assert tr.is_dir()

    def test_contains_template_files(self) -> None:
        root = packaged_templates_root()
        for locale_subdir in ("en", "tr"):
            templates = list((root / locale_subdir).glob("*.j2"))
            # 8 documents per locale
            assert len(templates) == 8

    def test_cached_returns_same_path(self) -> None:
        a = packaged_templates_root()
        b = packaged_templates_root()
        assert a == b


class TestIsPackagedTemplatesWritableCheck:
    def test_returns_ok_in_normal_install(self) -> None:
        ok, msg = is_packaged_templates_writable_check()
        assert ok is True
        assert "Templates available at" in msg

    def test_message_lists_locales(self) -> None:
        ok, msg = is_packaged_templates_writable_check()
        assert ok
        assert "en" in msg
        assert "tr" in msg
