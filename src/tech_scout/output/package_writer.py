"""Orchestrates writing the 8-document research package.

The package writer is the integration point between :class:`OutputDocSlot`
(language-neutral slot identifiers) and :class:`LocaleSpec` (per-locale
filenames + templates). The same analyzer JSON renders into either
language by routing each slot through the active locale.

A single writer instance accepts an optional ``slack_locale`` so callers
can render the slack-summary doc in a different language from the rest
of the package (a common product use case).
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from tech_scout.config.logging import get_logger
from tech_scout.domain.enums import OutputDocSlot
from tech_scout.domain.exceptions import TemplateRenderError
from tech_scout.locales.spec import LocaleSpec
from tech_scout.output.renderer import TemplateRenderer

log = get_logger(__name__)


class PackageWriter:
    """Render and write the 8-document package per locale.

    Construction takes:

    * ``renderer`` — a :class:`TemplateRenderer` rooted at ``templates/``
      (the parent of locale subdirectories).
    * ``output_folder`` — the destination directory for the rendered docs.
    * ``locale`` — the active :class:`LocaleSpec` (drives filenames and
      template paths for every slot).
    * ``slack_locale`` (optional) — overrides the locale for the
      :data:`OutputDocSlot.SLACK_SUMMARY` slot only.
    """

    def __init__(
        self,
        renderer: TemplateRenderer,
        output_folder: Path,
        locale: LocaleSpec,
        *,
        slack_locale: LocaleSpec | None = None,
    ) -> None:
        self._renderer = renderer
        self._output_folder = output_folder
        self._locale = locale
        self._slack_locale = slack_locale or locale

    @property
    def output_folder(self) -> Path:
        return self._output_folder

    @property
    def locale(self) -> LocaleSpec:
        return self._locale

    @property
    def slack_locale(self) -> LocaleSpec:
        return self._slack_locale

    def write_all(self, contexts: Mapping[OutputDocSlot, Mapping[str, Any]]) -> list[Path]:
        """Render every slot in :class:`OutputDocSlot` order.

        ``contexts`` must contain a key for each slot; missing keys raise
        :class:`TemplateRenderError`.
        """
        missing = [slot for slot in OutputDocSlot.in_order() if slot not in contexts]
        if missing:
            msg = "Missing render context for slots: " + ", ".join(s.value for s in missing)
            raise TemplateRenderError(
                msg,
                context={"missing_slots": [s.value for s in missing]},
            )

        written: list[Path] = []
        for slot in OutputDocSlot.in_order():
            target = self.write_doc(slot, contexts[slot])
            written.append(target)

        log.info(
            "package_written",
            output_folder=str(self._output_folder),
            doc_count=len(written),
            locale=self._locale.code,
            slack_locale=self._slack_locale.code,
        )
        return written

    def write_doc(self, slot: OutputDocSlot, context: Mapping[str, Any]) -> Path:
        locale = self._locale_for_slot(slot)
        target = self._output_folder / locale.filename_for(slot)
        return self._renderer.render_to_file(
            template_name=locale.template_path(slot),
            context=context,
            target=target,
        )

    def list_existing(self) -> list[Path]:
        if not self._output_folder.exists():
            return []
        existing: list[Path] = []
        for slot in OutputDocSlot.in_order():
            locale = self._locale_for_slot(slot)
            candidate = self._output_folder / locale.filename_for(slot)
            if candidate.is_file():
                existing.append(candidate)
        return existing

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _locale_for_slot(self, slot: OutputDocSlot) -> LocaleSpec:
        if slot == OutputDocSlot.SLACK_SUMMARY:
            return self._slack_locale
        return self._locale
