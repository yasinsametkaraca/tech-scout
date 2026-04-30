"""Output package — Jinja2 rendering and Phase 6 validation.

Used by Phase 5 (packaging) and Phase 6 (quality check). The skill calls
``ts_render_doc.py`` (which uses :class:`TemplateRenderer` +
:class:`PackageWriter` here) once per document, then
``ts_validate_package.py`` (which uses :class:`PackageValidator`) to verify
the output package.
"""

from __future__ import annotations

from tech_scout.output.package_writer import PackageWriter
from tech_scout.output.renderer import TemplateRenderer
from tech_scout.output.slug import slugify_topic, unique_run_slug
from tech_scout.output.validator import PackageValidator

__all__ = [
    "PackageValidator",
    "PackageWriter",
    "TemplateRenderer",
    "slugify_topic",
    "unique_run_slug",
]
