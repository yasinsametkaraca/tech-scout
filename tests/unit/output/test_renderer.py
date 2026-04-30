"""Unit tests for the Jinja2 template renderer."""

from __future__ import annotations

from pathlib import Path

import pytest

from tech_scout.domain.exceptions import TemplateRenderError
from tech_scout.output.renderer import TemplateRenderer, renderer_from_dict


class TestRendererBasic:
    def test_render_simple_template(self) -> None:
        r = renderer_from_dict({"hello.j2": "Hello {{ name }}"})
        out = r.render("hello.j2", {"name": "World"})
        assert out == "Hello World"

    def test_render_template_in_subdir(self) -> None:
        r = renderer_from_dict(
            {
                "en/hello.j2": "Hello {{ name }}",
                "tr/hello.j2": "Merhaba {{ name }}",
            }
        )
        assert r.render("en/hello.j2", {"name": "World"}) == "Hello World"
        assert r.render("tr/hello.j2", {"name": "Dünya"}) == "Merhaba Dünya"

    def test_strict_undefined_raises(self) -> None:
        r = renderer_from_dict({"x.j2": "Hello {{ missing_var }}"})
        with pytest.raises(TemplateRenderError):
            r.render("x.j2", {"name": "Y"})

    def test_template_not_found_raises(self) -> None:
        r = renderer_from_dict({"x.j2": "x"})
        with pytest.raises(TemplateRenderError):
            r.render("does_not_exist.j2", {})

    def test_render_to_file(self, tmp_path: Path) -> None:
        r = renderer_from_dict({"hello.j2": "{{ greeting }}"})
        target = tmp_path / "out.md"
        result = r.render_to_file("hello.j2", {"greeting": "Hi"}, target)
        assert result == target
        assert target.read_text(encoding="utf-8") == "Hi"

    def test_list_templates(self) -> None:
        r = renderer_from_dict({"a.j2": "x", "b.j2": "y"})
        templates = r.list_templates()
        assert templates == ["a.j2", "b.j2"]


class TestRendererFromFilesystem:
    def test_construct_from_existing_dir(self, tmp_path: Path) -> None:
        templates_root = tmp_path / "templates"
        templates_root.mkdir()
        (templates_root / "demo.j2").write_text("Hi {{ x }}", encoding="utf-8")
        r = TemplateRenderer(templates_root=templates_root)
        assert r.render("demo.j2", {"x": "world"}) == "Hi world"

    def test_construct_from_nonexistent_dir_raises(self, tmp_path: Path) -> None:
        with pytest.raises(TemplateRenderError):
            TemplateRenderer(templates_root=tmp_path / "missing")

    def test_construct_with_neither_raises(self) -> None:
        with pytest.raises(TemplateRenderError):
            TemplateRenderer()

    def test_locale_subdir_lookup(self, tmp_path: Path) -> None:
        templates_root = tmp_path / "templates"
        (templates_root / "en").mkdir(parents=True)
        (templates_root / "tr").mkdir(parents=True)
        (templates_root / "en" / "demo.j2").write_text("Hi {{ x }}", encoding="utf-8")
        (templates_root / "tr" / "demo.j2").write_text("Selam {{ x }}", encoding="utf-8")
        r = TemplateRenderer(templates_root=templates_root)
        assert r.render("en/demo.j2", {"x": "world"}) == "Hi world"
        assert r.render("tr/demo.j2", {"x": "dünya"}) == "Selam dünya"


class TestTitleCaseTrFilter:
    def test_dotted_i_handled(self) -> None:
        r = renderer_from_dict({"x.j2": "{{ s | title_case_tr }}"})
        out = r.render("x.j2", {"s": "istanbul başkenttir"})
        # Lowercase i must become İ, not I
        assert out.startswith("İstanbul")

    def test_dotless_i_handled(self) -> None:
        r = renderer_from_dict({"x.j2": "{{ s | title_case_tr }}"})
        out = r.render("x.j2", {"s": "ısı sıcak"})
        # ı must become I, not İ
        assert out.startswith("Isı")
