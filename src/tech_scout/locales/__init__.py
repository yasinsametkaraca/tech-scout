"""Locale layer — defines everything language-dependent for the package.

The package supports multiple output languages. Each language is described
by a single :class:`LocaleSpec` instance that carries:

* the output filenames for the 8 documents,
* the templates subdirectory under ``templates/``,
* the validator rules (required-section keywords, min-words),
* the verbatim Stage-A selection prompt,
* the labels used in the candidate display, and
* the final wrap-up template.

Library code looks locales up by code (``"en"``, ``"tr"``) or alias
(``"english"``, ``"turkish"``) via :func:`get_locale`. Helper scripts
expose the same lookup over JSON via ``ts_locale_info.py``.
"""

from __future__ import annotations

from tech_scout.locales.registry import (
    DEFAULT_LOCALE_CODE,
    LocaleRegistry,
    get_locale,
    get_locale_for_language,
    get_registry,
    list_locales,
)
from tech_scout.locales.spec import LocaleDocumentSpec, LocaleSpec

__all__ = [
    "DEFAULT_LOCALE_CODE",
    "LocaleDocumentSpec",
    "LocaleRegistry",
    "LocaleSpec",
    "get_locale",
    "get_locale_for_language",
    "get_registry",
    "list_locales",
]
