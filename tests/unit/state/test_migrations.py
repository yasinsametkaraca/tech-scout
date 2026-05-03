"""Unit tests for the state-migration framework."""

from __future__ import annotations

from typing import Any

import pytest

from tech_scout.domain.exceptions import StateStoreError
from tech_scout.state import migrations as migration_module
from tech_scout.state.migrations import (
    CURRENT_VERSIONS,
    _coerce_version,
    migrate,
    register_migration,
    supported_versions,
)


class TestCurrentVersions:
    def test_current_models_listed(self) -> None:
        # Sanity check: every persisted Pydantic model carries a version.
        assert set(CURRENT_VERSIONS.keys()) == {
            "RunSnapshot",
            "CandidateList",
            "UserSelection",
            "CodebaseProfile",
        }

    def test_current_versions_are_positive(self) -> None:
        for v in CURRENT_VERSIONS.values():
            assert v >= 1


class TestMigrate:
    def test_no_op_when_already_current(self) -> None:
        payload = {"schema_version": 1, "candidates": []}
        out = migrate("CandidateList", payload)
        assert out == payload

    def test_missing_version_treated_as_v1(self) -> None:
        payload = {"candidates": []}
        out = migrate("CandidateList", payload)
        # No migration runs because v1 is current; payload returned untouched
        assert out == payload

    def test_unknown_model_raises(self) -> None:
        with pytest.raises(StateStoreError):
            migrate("UnknownModel", {})

    def test_future_version_rejected(self) -> None:
        with pytest.raises(StateStoreError, match="declares schema_version=99"):
            migrate("CandidateList", {"schema_version": 99})


class TestCoerceVersion:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            (1, 1),
            (3, 3),
            (1.0, 1),
            (2.7, 2),
            ("3", 3),
            ("  4  ", 4),
            (None, 1),
            ("not-a-number", 1),
            (True, 1),
            ([], 1),
        ],
    )
    def test_coerce(self, raw: Any, expected: int) -> None:
        assert _coerce_version(raw) == expected


class TestRegisterMigration:
    def setup_method(self) -> None:
        # Save and restore the registry so test mutations don't leak.
        self._snapshot = {k: dict(v) for k, v in migration_module._REGISTRY.items()}
        self._versions_snapshot = dict(migration_module.CURRENT_VERSIONS)

    def teardown_method(self) -> None:
        migration_module._REGISTRY.clear()
        for k, v in self._snapshot.items():
            migration_module._REGISTRY[k] = dict(v)
        # Restore CURRENT_VERSIONS too (it's a Mapping but the underlying dict
        # is mutable in our test patches).
        if isinstance(migration_module.CURRENT_VERSIONS, dict):
            migration_module.CURRENT_VERSIONS.clear()  # type: ignore[attr-defined]
            migration_module.CURRENT_VERSIONS.update(self._versions_snapshot)  # type: ignore[attr-defined]

    def test_register_and_run(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Pretend CandidateList is at v2 and register a v1→v2 migration.
        monkeypatch.setitem(
            migration_module.CURRENT_VERSIONS,  # type: ignore[arg-type]
            "CandidateList",
            2,
        )

        @register_migration("CandidateList", from_version=1)
        def upgrade(payload: dict[str, Any]) -> dict[str, Any]:
            payload["new_field"] = "default"
            return payload

        out = migrate("CandidateList", {"schema_version": 1, "candidates": []})
        assert out["schema_version"] == 2
        assert out["new_field"] == "default"

    def test_duplicate_registration_rejected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setitem(
            migration_module.CURRENT_VERSIONS,  # type: ignore[arg-type]
            "CandidateList",
            3,
        )

        @register_migration("CandidateList", from_version=1)
        def upgrade1(payload: dict[str, Any]) -> dict[str, Any]:
            return payload

        with pytest.raises(ValueError, match="already registered"):

            @register_migration("CandidateList", from_version=1)
            def upgrade1b(payload: dict[str, Any]) -> dict[str, Any]:
                return payload

    def test_register_unknown_model_rejected(self) -> None:
        with pytest.raises(ValueError, match="Unknown model name"):

            @register_migration("Bogus", from_version=1)
            def upgrade(payload: dict[str, Any]) -> dict[str, Any]:
                return payload

    def test_register_invalid_from_version_rejected(self) -> None:
        with pytest.raises(ValueError, match="from_version"):

            @register_migration("CandidateList", from_version=0)
            def upgrade(payload: dict[str, Any]) -> dict[str, Any]:
                return payload

    def test_missing_step_in_chain_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Bump target to v3 but only register v1→v2; v2→v3 missing.
        monkeypatch.setitem(
            migration_module.CURRENT_VERSIONS,  # type: ignore[arg-type]
            "CandidateList",
            3,
        )

        @register_migration("CandidateList", from_version=1)
        def upgrade(payload: dict[str, Any]) -> dict[str, Any]:
            return payload

        with pytest.raises(StateStoreError, match="No migration registered"):
            migrate("CandidateList", {"schema_version": 1})


class TestSupportedVersions:
    def test_returns_range_to_current(self) -> None:
        # CandidateList is at v1 currently
        assert supported_versions("CandidateList") == (1,)

    def test_unknown_model_returns_empty(self) -> None:
        assert supported_versions("Bogus") == ()
