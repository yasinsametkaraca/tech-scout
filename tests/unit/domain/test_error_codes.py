"""Unit tests for the stable error-code registry and exception attachment."""

from __future__ import annotations

import pytest

from tech_scout.domain import error_codes
from tech_scout.domain.exceptions import (
    CodebaseScanError,
    ConfigurationError,
    HistoryLookupError,
    LocaleNotFoundError,
    StateStoreError,
    TechScoutError,
    TemplateRenderError,
    ValidationError,
)


class TestErrorCodeIdentifiers:
    @pytest.mark.parametrize(
        "code",
        list(error_codes.ALL_CODES),
    )
    def test_codes_are_upper_snake_case(self, code: str) -> None:
        assert code == code.upper()
        assert " " not in code
        assert "-" not in code

    def test_no_duplicate_codes(self) -> None:
        # ALL_CODES is a frozenset; size matches a manual count.
        assert len(error_codes.ALL_CODES) == 9


class TestExceptionAttachment:
    @pytest.mark.parametrize(
        ("exc_class", "expected_code"),
        [
            (TechScoutError, error_codes.INTERNAL_ERROR),
            (CodebaseScanError, error_codes.CODEBASE_SCAN_FAILED),
            (HistoryLookupError, error_codes.HISTORY_LOOKUP_FAILED),
            (StateStoreError, error_codes.STATE_STORE_ERROR),
            (TemplateRenderError, error_codes.TEMPLATE_RENDER_FAILED),
            (ValidationError, error_codes.PACKAGE_VALIDATION_FAILED),
            (ConfigurationError, error_codes.CONFIGURATION_INVALID),
            (LocaleNotFoundError, error_codes.LOCALE_NOT_FOUND),
        ],
    )
    def test_class_carries_expected_code(
        self,
        exc_class: type[TechScoutError],
        expected_code: str,
    ) -> None:
        assert exc_class.error_code == expected_code

    def test_to_dict_includes_error_code_and_type(self) -> None:
        err = ValidationError("bad", context={"x": 1})
        body = err.to_dict()
        assert body["error_code"] == error_codes.PACKAGE_VALIDATION_FAILED
        assert body["error_type"] == "ValidationError"
        assert body["message"] == "bad"
        assert body["context"] == {"x": 1}
