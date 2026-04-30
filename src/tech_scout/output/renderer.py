"""Jinja2 template renderer.

Single responsibility: load a template file by relative path and render it
with a provided context dict. Decoupled from filesystem layout via a
Protocol so tests can inject in-memory templates.

A renderer is bound to a single ``templates_root``. Locale-specific
templates live under ``templates_root/<locale.template_subdir>/`` and are
referenced by passing the relative path (e.g. ``"en/00-executive-summary.md.j2"``)
or by composing it from a :class:`~tech_scout.locales.spec.LocaleSpec`.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path, PurePosixPath
from typing import Any, Protocol, runtime_checkable

from jinja2 import (
    BaseLoader,
    DictLoader,
    Environment,
    FileSystemLoader,
    StrictUndefined,
    TemplateError,
    TemplateNotFound,
    select_autoescape,
)

from tech_scout.config.logging import get_logger
from tech_scout.domain.exceptions import TemplateRenderError

log = get_logger(__name__)


@runtime_checkable
class TemplateLoader(Protocol):
    """Abstract template source — file system, in-memory dict, etc."""

    def load(self, name: str) -> str:  # pragma: no cover - Protocol
        ...


class TemplateRenderer:
    """Jinja2 wrapper with strict undefined and md autoescape disabled.

    We disable autoescape because the output is markdown, not HTML. We
    enable :class:`StrictUndefined` so missing variables raise instead of
    silently rendering as empty.

    The renderer is locale-agnostic by design: it loads templates by
    relative path under ``templates_root``. Callers (or
    :class:`~tech_scout.output.package_writer.PackageWriter`) translate a
    locale + slot to a relative path before calling :meth:`render`.
    """

    def __init__(
        self,
        templates_root: Path | None = None,
        *,
        loader: BaseLoader | None = None,
    ) -> None:
        if loader is None:
            if templates_root is None:
                msg = "Either templates_root or loader must be provided"
                raise TemplateRenderError(msg)
            if not templates_root.is_dir():
                msg = f"Templates directory does not exist: {templates_root}"
                raise TemplateRenderError(msg, context={"templates_root": str(templates_root)})
            loader = FileSystemLoader(str(templates_root))

        self._env = Environment(
            loader=loader,
            autoescape=select_autoescape(default=False),
            undefined=StrictUndefined,
            keep_trailing_newline=True,
            trim_blocks=False,
            lstrip_blocks=False,
        )
        self._register_filters()

    def render(self, template_name: str | PurePosixPath, context: Mapping[str, Any]) -> str:
        name = str(template_name)
        try:
            template = self._env.get_template(name)
            return template.render(**dict(context))
        except TemplateNotFound as exc:
            msg = f"Template not found: {name}"
            raise TemplateRenderError(msg, context={"template_name": name}) from exc
        except TemplateError as exc:
            msg = f"Template render failed: {name} ({exc})"
            raise TemplateRenderError(
                msg,
                context={"template_name": name, "error": str(exc)},
            ) from exc

    def render_to_file(
        self,
        template_name: str | PurePosixPath,
        context: Mapping[str, Any],
        target: Path,
    ) -> Path:
        rendered = self.render(template_name, context)
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            target.write_text(rendered, encoding="utf-8")
        except OSError as exc:
            msg = f"Failed to write rendered output: {target}"
            raise TemplateRenderError(
                msg, context={"path": str(target), "error": str(exc)}
            ) from exc
        log.debug(
            "template_rendered",
            template=str(template_name),
            target=str(target),
            chars=len(rendered),
        )
        return target

    def list_templates(self) -> list[str]:
        return sorted(self._env.list_templates())

    def _register_filters(self) -> None:
        self._env.filters["title_case_tr"] = _title_case_tr


def renderer_from_dict(templates: Mapping[str, str]) -> TemplateRenderer:
    """Build a renderer backed by an in-memory dict (for tests)."""
    return TemplateRenderer(loader=DictLoader(dict(templates)))


def _title_case_tr(text: str) -> str:
    """Title-case that respects Turkish letter casing rules.

    Avoids the dotless-i pitfall: ``istanbul`` -> ``İstanbul`` (not ``Istanbul``).
    Used by Turkish templates; safe to invoke on non-Turkish text.
    """
    if not text:
        return text
    parts = text.split(" ")
    out: list[str] = []
    for word in parts:
        if not word:
            out.append(word)
            continue
        first = word[0]
        rest = word[1:]
        if first == "i":
            out.append("İ" + rest)
        elif first == "ı":
            out.append("I" + rest)
        else:
            out.append(first.upper() + rest)
    return " ".join(out)
