"""Registry of available locales.

Loads and exposes :class:`LocaleSpec` instances. Lookup is by ISO code
(``"en"``, ``"tr"``) or alias (``"english"``, ``"turkish"``).

Locales are registered explicitly here rather than auto-discovered so
the import graph is deterministic and adding one is a single, reviewable
edit.
"""

from __future__ import annotations

from collections.abc import Mapping

from tech_scout.domain.enums import Language
from tech_scout.domain.exceptions import LocaleNotFoundError
from tech_scout.locales.en import EN_LOCALE
from tech_scout.locales.spec import LocaleSpec
from tech_scout.locales.tr import TR_LOCALE

DEFAULT_LOCALE_CODE: str = "en"


class LocaleRegistry:
    """Holds registered :class:`LocaleSpec` instances and exposes lookup.

    The registry is constructed once at import time with the built-in
    locales. Tests can construct their own registry with custom specs.
    """

    def __init__(self, specs: Mapping[str, LocaleSpec]) -> None:
        seen_codes: set[str] = set()
        seen_languages: set[Language] = set()
        for code, spec in specs.items():
            if code != spec.code:
                msg = f"Registry key {code!r} does not match spec.code {spec.code!r}"
                raise ValueError(msg)
            if spec.code in seen_codes:
                msg = f"Duplicate locale code: {spec.code!r}"
                raise ValueError(msg)
            if spec.language in seen_languages:
                msg = (
                    f"Locale {spec.code!r} reuses Language enum value "
                    f"{spec.language.value!r} — each Language must map to one locale"
                )
                raise ValueError(msg)
            seen_codes.add(spec.code)
            seen_languages.add(spec.language)
        self._specs: dict[str, LocaleSpec] = dict(specs)

    def get(self, code_or_alias: str) -> LocaleSpec:
        """Return the spec matching *code_or_alias* (case-insensitive).

        Raises :class:`LocaleNotFoundError` if no match is registered.
        """
        normalized = code_or_alias.strip().lower()
        for spec in self._specs.values():
            if spec.matches(normalized):
                return spec
        msg = f"No locale registered for {code_or_alias!r}. Available: {sorted(self.codes())}"
        raise LocaleNotFoundError(msg, context={"requested": code_or_alias})

    def for_language(self, language: Language) -> LocaleSpec:
        """Return the spec matching the given :class:`Language` enum value."""
        for spec in self._specs.values():
            if spec.language == language:
                return spec
        msg = f"No locale registered for Language.{language.name}"
        raise LocaleNotFoundError(msg, context={"language": language.value})

    def codes(self) -> tuple[str, ...]:
        """Return all registered locale codes."""
        return tuple(self._specs.keys())

    def all(self) -> tuple[LocaleSpec, ...]:
        """Return all registered specs in insertion order."""
        return tuple(self._specs.values())


_DEFAULT_REGISTRY = LocaleRegistry(
    {
        EN_LOCALE.code: EN_LOCALE,
        TR_LOCALE.code: TR_LOCALE,
    }
)


def get_registry() -> LocaleRegistry:
    """Return the shared default registry (built-in locales)."""
    return _DEFAULT_REGISTRY


def get_locale(code_or_alias: str) -> LocaleSpec:
    """Convenience: look up a locale in the default registry."""
    return _DEFAULT_REGISTRY.get(code_or_alias)


def get_locale_for_language(language: Language) -> LocaleSpec:
    """Convenience: look up a locale by :class:`Language` enum."""
    return _DEFAULT_REGISTRY.for_language(language)


def list_locales() -> tuple[LocaleSpec, ...]:
    """Convenience: list all registered specs."""
    return _DEFAULT_REGISTRY.all()
