"""Read/write JSON state files for a single run.

All read paths go through Pydantic validation so a malformed state file
is caught at boundary instead of corrupting downstream phases.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError as PydanticValidationError

from tech_scout.config.logging import get_logger
from tech_scout.domain.exceptions import StateStoreError
from tech_scout.domain.models import (
    CandidateList,
    CodebaseProfile,
    RunSnapshot,
    UserSelection,
)
from tech_scout.domain.value_objects import RunId
from tech_scout.state.schemas import (
    CANDIDATES_FILENAME,
    CODEBASE_PROFILE_FILENAME,
    PHASE_PROGRESS_FILENAME,
    SELECTION_FILENAME,
    STATE_DIR_NAME,
    STATE_FILENAME,
)
from tech_scout.utils.path_safety import ensure_directory

log = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)


class StateStore:
    """Read/write the per-run state directory.

    Construct with the output folder (where the package will be written).
    The state directory ``<output-folder>/.tech-scout/<run-id>/`` is created
    on first write. Reads of missing files return ``None`` rather than
    raising, except where indicated.
    """

    def __init__(self, output_folder: Path, run_id: RunId | str) -> None:
        self._output_folder = output_folder
        self._run_id = run_id if isinstance(run_id, RunId) else RunId(value=str(run_id))
        self._state_dir = output_folder / STATE_DIR_NAME / str(self._run_id)

    @property
    def state_dir(self) -> Path:
        return self._state_dir

    @property
    def run_id(self) -> RunId:
        return self._run_id

    def initialize(self) -> Path:
        """Create the state directory if it doesn't exist; return the path."""
        return ensure_directory(self._state_dir)

    # --- Generic helpers ---------------------------------------------------

    def write_model(self, filename: str, model: BaseModel) -> Path:
        target = self._target(filename)
        ensure_directory(target.parent)
        try:
            target.write_text(
                model.model_dump_json(indent=2, by_alias=False),
                encoding="utf-8",
            )
        except OSError as exc:
            msg = f"Failed to write state file {target}: {exc}"
            raise StateStoreError(
                msg,
                context={"path": str(target), "filename": filename},
            ) from exc
        log.debug("state_written", filename=filename, path=str(target))
        return target

    def read_model(self, filename: str, model_class: type[T]) -> T | None:
        target = self._target(filename)
        if not target.is_file():
            return None
        try:
            text = target.read_text(encoding="utf-8")
        except OSError as exc:
            msg = f"Failed to read state file {target}: {exc}"
            raise StateStoreError(
                msg,
                context={"path": str(target), "filename": filename},
            ) from exc

        try:
            data: Any = json.loads(text)
        except json.JSONDecodeError as exc:
            msg = f"State file is not valid JSON: {target}"
            raise StateStoreError(
                msg,
                context={"path": str(target), "filename": filename},
            ) from exc

        try:
            return model_class.model_validate(data)
        except PydanticValidationError as exc:
            msg = f"State file failed schema validation: {target}"
            raise StateStoreError(
                msg,
                context={
                    "path": str(target),
                    "filename": filename,
                    "errors": exc.errors(),
                },
            ) from exc

    # --- Typed convenience methods ----------------------------------------

    def write_run_snapshot(self, snapshot: RunSnapshot) -> Path:
        return self.write_model(STATE_FILENAME, snapshot)

    def read_run_snapshot(self) -> RunSnapshot | None:
        return self.read_model(STATE_FILENAME, RunSnapshot)

    def write_candidates(self, candidates: CandidateList) -> Path:
        return self.write_model(CANDIDATES_FILENAME, candidates)

    def read_candidates(self) -> CandidateList | None:
        return self.read_model(CANDIDATES_FILENAME, CandidateList)

    def write_selection(self, selection: UserSelection) -> Path:
        return self.write_model(SELECTION_FILENAME, selection)

    def read_selection(self) -> UserSelection | None:
        return self.read_model(SELECTION_FILENAME, UserSelection)

    def write_codebase_profile(self, profile: CodebaseProfile) -> Path:
        return self.write_model(CODEBASE_PROFILE_FILENAME, profile)

    def read_codebase_profile(self) -> CodebaseProfile | None:
        return self.read_model(CODEBASE_PROFILE_FILENAME, CodebaseProfile)

    # --- Phase progress (small JSON object, not a domain model) -----------

    def write_phase_progress(self, progress: dict[str, str]) -> Path:
        target = self._target(PHASE_PROGRESS_FILENAME)
        ensure_directory(target.parent)
        try:
            target.write_text(json.dumps(progress, indent=2, sort_keys=True), encoding="utf-8")
        except OSError as exc:
            msg = f"Failed to write phase progress: {exc}"
            raise StateStoreError(msg, context={"path": str(target)}) from exc
        return target

    def read_phase_progress(self) -> dict[str, str] | None:
        target = self._target(PHASE_PROGRESS_FILENAME)
        if not target.is_file():
            return None
        try:
            text = target.read_text(encoding="utf-8")
        except OSError as exc:
            msg = f"Failed to read phase progress: {exc}"
            raise StateStoreError(msg, context={"path": str(target)}) from exc
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            msg = f"Phase progress JSON is malformed: {target}"
            raise StateStoreError(msg, context={"path": str(target)}) from exc
        if not isinstance(data, dict):
            msg = f"Phase progress must be a JSON object: {target}"
            raise StateStoreError(msg, context={"path": str(target)})
        return {str(k): str(v) for k, v in data.items()}

    # --- Internal ---------------------------------------------------------

    def _target(self, filename: str) -> Path:
        if "/" in filename or "\\" in filename:
            msg = f"State filename must not contain path separators: {filename!r}"
            raise StateStoreError(msg, context={"filename": filename})
        return self._state_dir / filename
