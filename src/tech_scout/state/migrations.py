"""Schema-version migrations for persisted state files.

Every persisted Pydantic model carries a top-level ``schema_version: int``
field. When :class:`tech_scout.state.store.StateStore` reads a state file,
it inspects the JSON's ``schema_version`` (defaulting to 1 if absent — that
is, files written before versioning was introduced) and runs the migration
chain forward to the model's current version before validation.

Adding a new migration:

1. Bump the ``schema_version`` default on the model in
   :mod:`tech_scout.domain.models`.
2. Bump the matching constant in :data:`CURRENT_VERSIONS` below.
3. Register the upgrade function via :func:`register_migration`.

Migrations operate on plain ``dict`` payloads, not Pydantic instances —
the model class shape may have changed, so we cannot rely on the new
schema until the migration completes. Each migration takes a v_N dict and
returns a v_{N+1} dict.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any, Final

from tech_scout.domain.exceptions import StateStoreError

MigrationPayload = dict[str, Any]
"""Mutable JSON payload — what a migration receives and returns."""

MigrationFn = Callable[[MigrationPayload], MigrationPayload]
"""A single from-version→to-version transformation."""


CURRENT_VERSIONS: Final[Mapping[str, int]] = {
    "RunSnapshot": 1,
    "CandidateList": 1,
    "UserSelection": 1,
    "CodebaseProfile": 1,
}
"""The current schema version for each persisted model.

Keys are the unqualified class names (``__name__``). Bump when the model's
shape changes in a backwards-incompatible way and add a matching migration.
"""


_REGISTRY: dict[str, dict[int, MigrationFn]] = {name: {} for name in CURRENT_VERSIONS}


def register_migration(
    model_name: str, *, from_version: int
) -> Callable[[MigrationFn], MigrationFn]:
    """Decorator to register a v_N → v_{N+1} migration for *model_name*.

    Usage::

        @register_migration("CandidateList", from_version=1)
        def _candidate_list_v1_to_v2(payload: dict[str, Any]) -> dict[str, Any]:
            payload["new_field"] = "default"
            return payload

    Raises :class:`ValueError` if a migration is already registered for the
    same ``(model_name, from_version)`` pair, so a typo doesn't silently
    overwrite an existing migration.
    """
    if model_name not in CURRENT_VERSIONS:
        msg = f"Unknown model name {model_name!r}. Add it to CURRENT_VERSIONS first."
        raise ValueError(msg)
    if from_version < 1:
        msg = f"from_version must be >= 1, got {from_version}"
        raise ValueError(msg)

    def decorator(fn: MigrationFn) -> MigrationFn:
        bucket = _REGISTRY[model_name]
        if from_version in bucket:
            msg = (
                f"Migration {model_name} v{from_version}→v{from_version + 1} "
                f"already registered as {bucket[from_version].__qualname__}"
            )
            raise ValueError(msg)
        bucket[from_version] = fn
        return fn

    return decorator


def migrate(model_name: str, payload: MigrationPayload) -> MigrationPayload:
    """Run *payload* through every registered migration up to the current version.

    The payload's ``schema_version`` field drives the chain. Missing or
    falsy ``schema_version`` is treated as version 1 so files written before
    the field existed remain readable.

    Raises :class:`StateStoreError` if:

    * the recorded version is newer than this code knows about (downgrade),
    * a required migration step is not registered (gap in the chain).
    """
    if model_name not in CURRENT_VERSIONS:
        msg = f"Unknown model name {model_name!r}"
        raise StateStoreError(msg, context={"model_name": model_name})

    target = CURRENT_VERSIONS[model_name]
    current = max(_coerce_version(payload.get("schema_version")), 1)

    if current > target:
        msg = (
            f"State file for {model_name} declares schema_version={current}, "
            f"but this build only supports up to v{target}. Upgrade tech-scout."
        )
        raise StateStoreError(
            msg,
            context={
                "model_name": model_name,
                "stored_version": current,
                "supported_version": target,
            },
        )

    bucket = _REGISTRY[model_name]
    while current < target:
        step = bucket.get(current)
        if step is None:
            msg = (
                f"No migration registered for {model_name} v{current}→v{current + 1}. "
                "This is a programming error: bumping CURRENT_VERSIONS requires "
                "a matching @register_migration."
            )
            raise StateStoreError(
                msg,
                context={
                    "model_name": model_name,
                    "missing_step_from": current,
                    "missing_step_to": current + 1,
                },
            )
        payload = step(payload)
        payload["schema_version"] = current + 1
        current += 1
    return payload


def _coerce_version(raw: Any) -> int:
    """Best-effort conversion of an arbitrary JSON value to a positive int.

    Old state files written before versioning was introduced have no
    ``schema_version`` field and surface as ``None`` here. Anything that
    cannot be coerced to a positive integer maps to ``1`` so the migration
    chain treats them as the original schema.
    """
    if isinstance(raw, bool):
        return 1
    if isinstance(raw, int):
        return raw
    if isinstance(raw, float):
        return int(raw)
    if isinstance(raw, str) and raw.strip().isdigit():
        return int(raw.strip())
    return 1


def supported_versions(model_name: str) -> tuple[int, ...]:
    """Return the (sorted) versions the registry knows how to read for *model_name*.

    Includes the current target version. For ``model_name`` with N
    registered migrations, this returns ``(1, 2, ..., target)``.
    """
    if model_name not in CURRENT_VERSIONS:
        return ()
    return tuple(range(1, CURRENT_VERSIONS[model_name] + 1))


__all__ = [
    "CURRENT_VERSIONS",
    "MigrationFn",
    "MigrationPayload",
    "migrate",
    "register_migration",
    "supported_versions",
]
