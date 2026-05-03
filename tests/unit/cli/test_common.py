"""Unit tests for the CLI common helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from tech_scout.cli._common import (
    ENVELOPE_VERSION,
    emit_error,
    emit_success,
    parse_path,
    repo_root,
    run_script,
)
from tech_scout.domain import error_codes
from tech_scout.domain.exceptions import ValidationError


def _capture_envelope(capsys: pytest.CaptureFixture[str]) -> dict[str, Any]:
    """Pull the JSON envelope a script wrote to stdout."""
    captured = capsys.readouterr()
    return json.loads(captured.out)


class TestEmitSuccess:
    def test_writes_versioned_envelope(self, capsys: pytest.CaptureFixture[str]) -> None:
        with pytest.raises(SystemExit) as exc:
            emit_success({"hello": "world"})
        assert exc.value.code == 0
        envelope = _capture_envelope(capsys)
        assert envelope == {
            "envelope_version": ENVELOPE_VERSION,
            "status": "ok",
            "data": {"hello": "world"},
        }

    def test_custom_exit_code(self, capsys: pytest.CaptureFixture[str]) -> None:
        with pytest.raises(SystemExit) as exc:
            emit_success({}, exit_code=7)
        assert exc.value.code == 7


class TestEmitError:
    def test_domain_error_uses_class_error_code(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        with pytest.raises(SystemExit) as exc:
            emit_error(ValidationError("bad", context={"k": 1}))
        assert exc.value.code == 1
        envelope = _capture_envelope(capsys)
        assert envelope["status"] == "error"
        assert envelope["data"]["error_code"] == error_codes.PACKAGE_VALIDATION_FAILED
        assert envelope["data"]["error_type"] == "ValidationError"
        assert envelope["data"]["context"] == {"k": 1}

    def test_unknown_exception_uses_internal_error(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        with pytest.raises(SystemExit):
            emit_error(RuntimeError("boom"))
        envelope = _capture_envelope(capsys)
        assert envelope["data"]["error_code"] == error_codes.INTERNAL_ERROR
        assert envelope["data"]["error_type"] == "RuntimeError"

    def test_explicit_error_code_overrides(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        with pytest.raises(SystemExit):
            emit_error(
                RuntimeError("interrupted"),
                exit_code=130,
                error_code=error_codes.USER_INTERRUPTED,
            )
        envelope = _capture_envelope(capsys)
        assert envelope["data"]["error_code"] == error_codes.USER_INTERRUPTED


class TestRunScript:
    def test_returns_dict_emits_success(self, capsys: pytest.CaptureFixture[str]) -> None:
        def main() -> dict[str, Any]:
            return {"answer": 42}

        with pytest.raises(SystemExit) as exc:
            run_script(main)
        assert exc.value.code == 0
        envelope = _capture_envelope(capsys)
        assert envelope["status"] == "ok"
        assert envelope["data"] == {"answer": 42}

    def test_domain_error_emits_error_envelope(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        def main() -> dict[str, Any]:
            raise ValidationError("nope", context={"why": "test"})

        with pytest.raises(SystemExit) as exc:
            run_script(main)
        assert exc.value.code == 1
        envelope = _capture_envelope(capsys)
        assert envelope["data"]["error_code"] == error_codes.PACKAGE_VALIDATION_FAILED

    def test_unexpected_exception_uses_internal_error(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        def main() -> dict[str, Any]:
            raise RuntimeError("unexpected")

        with pytest.raises(SystemExit) as exc:
            run_script(main)
        assert exc.value.code == 2
        envelope = _capture_envelope(capsys)
        assert envelope["data"]["error_code"] == error_codes.INTERNAL_ERROR

    def test_keyboard_interrupt_translates_to_user_interrupted(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        def main() -> dict[str, Any]:
            raise KeyboardInterrupt

        with pytest.raises(SystemExit) as exc:
            run_script(main)
        assert exc.value.code == 130
        envelope = _capture_envelope(capsys)
        assert envelope["data"]["error_code"] == error_codes.USER_INTERRUPTED


class TestParsePath:
    def test_expands_user_dir(self) -> None:
        path = parse_path("~/foo")
        assert "~" not in str(path)
        assert path.is_absolute()

    def test_resolves_relative(self, tmp_path: Path) -> None:
        path = parse_path(str(tmp_path / "subdir" / ".." / "subdir"))
        assert path.is_absolute()
        assert "subdir" in path.parts


class TestRepoRoot:
    def test_returns_a_path(self) -> None:
        root = repo_root()
        assert isinstance(root, Path)
        # In source-checkout mode we expect pyproject.toml to exist
        assert (root / "pyproject.toml").is_file() or root == Path.cwd()
