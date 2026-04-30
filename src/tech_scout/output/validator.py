"""Phase 6 quality check.

After Phase 5 writes the package, the skill calls ``ts_validate_package.py``
which uses :class:`PackageValidator` to check structural and content
invariants. The validator is locale-aware: it consults the active
:class:`~tech_scout.locales.spec.LocaleSpec` for expected filenames,
required-section keywords, and minimum word counts.

The result is a :class:`~tech_scout.domain.models.ValidationReport` that
the skill consumes to decide whether to regenerate any document.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from pathlib import Path

from tech_scout.config.logging import get_logger
from tech_scout.domain.enums import OutputDocSlot
from tech_scout.domain.exceptions import ValidationError
from tech_scout.domain.models import ValidationIssue, ValidationReport
from tech_scout.locales.spec import LocaleDocumentSpec, LocaleSpec

log = get_logger(__name__)


_HEADING = re.compile(r"^#{1,6}\s+\S", re.MULTILINE)
_LINK = re.compile(r"\[([^\]]+)]\(([^)]+)\)")
_MERMAID_FENCE = re.compile(r"^```mermaid\b", re.MULTILINE)


class PackageValidator:
    """Check a generated package for structural completeness.

    Constructed with the active package locale and (optionally) a
    different slack locale — matching the writer's contract.
    """

    def __init__(
        self,
        locale: LocaleSpec,
        *,
        slack_locale: LocaleSpec | None = None,
    ) -> None:
        self._locale = locale
        self._slack_locale = slack_locale or locale

    @property
    def locale(self) -> LocaleSpec:
        return self._locale

    @property
    def slack_locale(self) -> LocaleSpec:
        return self._slack_locale

    def validate(self, package_path: Path) -> ValidationReport:
        if not package_path.exists():
            msg = f"Package path does not exist: {package_path}"
            raise ValidationError(msg, context={"path": str(package_path)})
        if not package_path.is_dir():
            msg = f"Package path is not a directory: {package_path}"
            raise ValidationError(msg, context={"path": str(package_path)})

        present: list[str] = []
        missing: list[str] = []
        issues: list[ValidationIssue] = []

        for slot in OutputDocSlot.in_order():
            doc_spec = self._locale_for_slot(slot).document(slot)
            file_path = package_path / doc_spec.filename
            if not file_path.is_file():
                missing.append(doc_spec.filename)
                issues.append(
                    ValidationIssue(
                        severity="error",
                        document=doc_spec.filename,
                        message=f"Required document missing: {doc_spec.filename}",
                    )
                )
                continue
            present.append(doc_spec.filename)
            issues.extend(self._validate_doc(slot, doc_spec, file_path))

        report = ValidationReport(
            package_path=package_path,
            issues=tuple(issues),
            documents_present=tuple(present),
            documents_missing=tuple(missing),
        )
        log.info(
            "package_validated",
            path=str(package_path),
            errors=report.error_count,
            warnings=report.warning_count,
            missing=len(missing),
            locale=self._locale.code,
            slack_locale=self._slack_locale.code,
        )
        return report

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _locale_for_slot(self, slot: OutputDocSlot) -> LocaleSpec:
        if slot == OutputDocSlot.SLACK_SUMMARY:
            return self._slack_locale
        return self._locale

    def _validate_doc(
        self,
        slot: OutputDocSlot,
        doc_spec: LocaleDocumentSpec,
        path: Path,
    ) -> Iterable[ValidationIssue]:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            yield ValidationIssue(
                severity="error",
                document=doc_spec.filename,
                message=f"Cannot read document: {exc}",
            )
            return

        # Word count
        word_count = len(text.split())
        if word_count < doc_spec.min_words:
            yield ValidationIssue(
                severity="warning",
                document=doc_spec.filename,
                message=(
                    f"Document is shorter than expected minimum: "
                    f"{word_count} words < {doc_spec.min_words} expected"
                ),
            )

        # At least one heading
        if not _HEADING.search(text):
            yield ValidationIssue(
                severity="error",
                document=doc_spec.filename,
                message="No markdown heading found — document appears empty or malformed",
            )

        # Required sections
        if doc_spec.required_section_keywords:
            lowered = text.lower()
            for keyword in doc_spec.required_section_keywords:
                if keyword not in lowered:
                    yield ValidationIssue(
                        severity="warning",
                        document=doc_spec.filename,
                        section=keyword,
                        message=f"Expected section keyword not found: '{keyword}'",
                    )

        # Broken Jinja markers
        if "{{" in text or "{%" in text:
            yield ValidationIssue(
                severity="error",
                document=doc_spec.filename,
                message="Unrendered Jinja2 markers ({{ or {%) found — render likely failed",
            )

        # Diagrams should have at least one mermaid block
        if slot == OutputDocSlot.DIAGRAMS and not _MERMAID_FENCE.search(text):
            yield ValidationIssue(
                severity="warning",
                document=doc_spec.filename,
                message="No mermaid diagram fences found in diagram document",
            )

        # Sources should have at least one link
        if slot == OutputDocSlot.SOURCES and not _LINK.search(text):
            yield ValidationIssue(
                severity="warning",
                document=doc_spec.filename,
                message="No markdown links found in sources document",
            )
