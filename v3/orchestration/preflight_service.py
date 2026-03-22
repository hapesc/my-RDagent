"""Canonical Phase 23 preflight truth for stage recommendations and entry."""

from __future__ import annotations

import re
import tomllib
from collections.abc import Callable
from pathlib import Path
from typing import Any

from v3.contracts.preflight import (
    PreflightBlocker,
    PreflightBlockerCategory,
    PreflightBlockersByCategory,
    PreflightReadiness,
    PreflightResult,
)
from v3.contracts.stage import StageKey, StageSnapshot, StageStatus
from v3.ports.state_store import StateStorePort

_CATEGORY_ORDER: tuple[PreflightBlockerCategory, ...] = (
    PreflightBlockerCategory.STATE,
    PreflightBlockerCategory.ARTIFACT,
    PreflightBlockerCategory.RECOVERY,
    PreflightBlockerCategory.RUNTIME,
    PreflightBlockerCategory.DEPENDENCY,
)
_DEFAULT_PASS_ACTION = "None - canonical preflight truth passed."
_IMPORT_ALIASES: dict[str, tuple[str, ...]] = {
    "pydantic": ("pydantic",),
    "pytest": ("pytest",),
    "import_linter": ("import_linter", "importlinter"),
}


class PreflightService:
    """Read-only executability gate for Phase 23 runtime/state truth."""

    def __init__(
        self,
        state_store: StateStorePort,
        *,
        project_root: str | Path = ".",
        python_version_provider: Callable[[], tuple[int, int, int]] | None = None,
        command_exists_provider: Callable[[str], bool] | None = None,
        module_exists_provider: Callable[[str], bool] | None = None,
    ) -> None:
        self._state_store = state_store
        self._project_root = Path(project_root)
        self._python_version_provider = python_version_provider or self._default_python_version
        self._command_exists_provider = command_exists_provider or self._default_command_exists
        self._module_exists_provider = module_exists_provider or self._default_module_exists

    def assess(
        self,
        *,
        run_id: str,
        branch_id: str,
        stage_key: StageKey,
        recommended_next_skill: str,
    ) -> PreflightResult:
        project_metadata = self._load_project_metadata()
        blockers = PreflightBlockersByCategory()
        self._check_runtime(blockers, project_metadata)
        self._check_dependencies(blockers, project_metadata, stage_key)

        branch = self._state_store.load_branch_snapshot(branch_id)
        run = self._state_store.load_run_snapshot(run_id)
        stage = self._state_store.load_stage_snapshot(branch_id, stage_key)

        state_ready = self._check_state(
            blockers=blockers,
            run_id=run_id,
            branch_id=branch_id,
            stage_key=stage_key,
            run=run,
            branch=branch,
            stage=stage,
        )
        if state_ready:
            self._check_artifacts(
                blockers=blockers,
                run_id=run_id,
                branch_id=branch_id,
                stage_key=stage_key,
                stage=stage,
            )
            self._check_recovery(
                blockers=blockers,
                branch_id=branch_id,
                stage_key=stage_key,
                stage=stage,
            )

        primary = self._primary_blocker(blockers)
        return PreflightResult(
            run_id=run_id,
            branch_id=branch_id,
            stage_key=stage_key,
            recommended_next_skill=recommended_next_skill,
            readiness=(
                PreflightReadiness.BLOCKED
                if primary is not None
                else PreflightReadiness.EXECUTABLE
            ),
            primary_blocker_category=None if primary is None else primary.category,
            primary_blocker_reason=None if primary is None else primary.reason,
            repair_action=_DEFAULT_PASS_ACTION if primary is None else primary.repair_action,
            blockers_by_category=blockers,
        )

    def _check_runtime(self, blockers: PreflightBlockersByCategory, metadata: dict[str, Any]) -> None:
        requires_python = metadata.get("requires_python")
        if not isinstance(requires_python, str) or not requires_python.strip():
            self._add_blocker(
                blockers,
                PreflightBlockerCategory.RUNTIME,
                "Project runtime requirement is missing from pyproject.toml.",
                "Restore `[project].requires-python` in pyproject.toml before continuing.",
            )
        else:
            required_version = self._parse_minimum_python_version(requires_python)
            current_version = self._python_version_provider()
            if required_version is None:
                self._add_blocker(
                    blockers,
                    PreflightBlockerCategory.RUNTIME,
                    f"Project runtime requirement '{requires_python}' could not be interpreted safely.",
                    "Use a simple minimum Python constraint such as `>=3.11` in pyproject.toml.",
                )
            elif current_version < required_version:
                self._add_blocker(
                    blockers,
                    PreflightBlockerCategory.RUNTIME,
                    (
                        f"Python {current_version[0]}.{current_version[1]}.{current_version[2]} does not satisfy "
                        f"the project requirement {requires_python}."
                    ),
                    f"Switch to Python {requires_python} and rerun `uv sync --extra test`.",
                )

        if not self._command_exists_provider("uv"):
            self._add_blocker(
                blockers,
                PreflightBlockerCategory.RUNTIME,
                "Required runtime command `uv` is not available in the current environment.",
                "Install uv, then rerun `uv sync --extra test` before continuing.",
            )

    def _check_dependencies(
        self,
        blockers: PreflightBlockersByCategory,
        metadata: dict[str, Any],
        stage_key: StageKey,
    ) -> None:
        dependencies = self._normalize_dependency_names(metadata.get("dependencies"))
        optional_dependencies = metadata.get("optional_dependencies", {})
        test_dependencies = self._normalize_dependency_names(optional_dependencies.get("test", []))

        required_modules: list[str] = []
        if "pydantic" in dependencies:
            required_modules.append("pydantic")
        if stage_key is StageKey.VERIFY:
            if "pytest" in test_dependencies:
                required_modules.append("pytest")
            if "import-linter" in test_dependencies:
                required_modules.append("import_linter")

        missing_modules = [
            module_name
            for module_name in required_modules
            if not self._module_available(module_name)
        ]
        if missing_modules:
            joined = ", ".join(missing_modules)
            self._add_blocker(
                blockers,
                PreflightBlockerCategory.DEPENDENCY,
                f"Required Python dependencies are missing for this stage: {joined}.",
                f"Run `uv sync --extra test` to install the missing dependencies: {joined}.",
            )

    def _check_state(
        self,
        *,
        blockers: PreflightBlockersByCategory,
        run_id: str,
        branch_id: str,
        stage_key: StageKey,
        run: Any,
        branch: Any,
        stage: StageSnapshot | None,
    ) -> bool:
        if run is None:
            self._add_blocker(
                blockers,
                PreflightBlockerCategory.STATE,
                f"Run snapshot {run_id} is missing from canonical V3 state.",
                f"Repair persisted run/branch/stage snapshots so run {run_id} exists before continuing.",
            )
            return False
        if branch is None:
            self._add_blocker(
                blockers,
                PreflightBlockerCategory.STATE,
                f"Branch snapshot {branch_id} is missing from canonical V3 state.",
                f"Repair persisted run/branch/stage snapshots so branch {branch_id} exists before continuing.",
            )
            return False
        if branch.run_id != run_id:
            self._add_blocker(
                blockers,
                PreflightBlockerCategory.STATE,
                f"Branch {branch_id} belongs to run {branch.run_id}, not requested run {run_id}.",
                f"Repair persisted run/branch/stage snapshots so run {run_id} and branch {branch_id} agree before continuing.",
            )
            return False
        if stage is None:
            self._add_blocker(
                blockers,
                PreflightBlockerCategory.STATE,
                f"Stage snapshot {stage_key.value} is missing for branch {branch_id}.",
                f"Repair persisted run/branch/stage snapshots so {stage_key.value} exists for branch {branch_id}.",
            )
            return False
        if branch.current_stage_key != stage_key:
            self._add_blocker(
                blockers,
                PreflightBlockerCategory.STATE,
                (
                    f"Branch {branch_id} current_stage_key is {branch.current_stage_key.value}, "
                    f"not {stage_key.value}."
                ),
                "Repair persisted run/branch/stage snapshots so current_stage_key matches the executing stage.",
            )
            return False

        embedded_stage = self._matching_branch_stage(branch.stages, stage_key)
        if embedded_stage is None:
            self._add_blocker(
                blockers,
                PreflightBlockerCategory.STATE,
                f"Branch {branch_id} does not embed a {stage_key.value} stage snapshot.",
                f"Repair persisted run/branch/stage snapshots so branch {branch_id} embeds the {stage_key.value} stage.",
            )
            return False
        if embedded_stage != stage:
            self._add_blocker(
                blockers,
                PreflightBlockerCategory.STATE,
                f"Branch {branch_id} embeds stale {stage_key.value} stage truth that disagrees with the latest snapshot on disk.",
                "Repair persisted run/branch/stage snapshots so embedded branch state and latest stage snapshots match.",
            )
            return False
        return True

    def _check_artifacts(
        self,
        *,
        blockers: PreflightBlockersByCategory,
        run_id: str,
        branch_id: str,
        stage_key: StageKey,
        stage: StageSnapshot | None,
    ) -> None:
        if stage is None or not stage.artifact_ids:
            return
        artifacts = self._state_store.list_artifact_snapshots(
            run_id,
            branch_id=branch_id,
            stage_key=stage_key,
        )
        artifacts_by_id = {artifact.artifact_id for artifact in artifacts}
        missing_artifacts = [
            artifact_id for artifact_id in stage.artifact_ids if artifact_id not in artifacts_by_id
        ]
        if missing_artifacts:
            missing = ", ".join(missing_artifacts)
            self._add_blocker(
                blockers,
                PreflightBlockerCategory.ARTIFACT,
                f"Stage {stage_key.value} references missing artifact snapshots: {missing}.",
                f"Rebuild or republish {stage_key.value} artifacts so these snapshots exist: {missing}.",
            )

    def _check_recovery(
        self,
        *,
        blockers: PreflightBlockersByCategory,
        branch_id: str,
        stage_key: StageKey,
        stage: StageSnapshot | None,
    ) -> None:
        if stage is None or stage.status is not StageStatus.COMPLETED:
            return
        assessment = self._state_store.load_recovery_assessment(branch_id, stage_key)
        if assessment is None:
            self._add_blocker(
                blockers,
                PreflightBlockerCategory.RECOVERY,
                (
                    f"Completed stage {stage_key.value} has result artifacts but no persisted recovery assessment "
                    "to prove reuse or replay truth."
                ),
                f"Persist a recovery assessment for {stage_key.value} before reusing completed results.",
            )

    def _load_project_metadata(self) -> dict[str, Any]:
        pyproject_path = self._project_root / "pyproject.toml"
        if not pyproject_path.exists():
            return {"requires_python": None, "dependencies": [], "optional_dependencies": {}}
        data = tomllib.loads(pyproject_path.read_text())
        project = data.get("project", {})
        return {
            "requires_python": project.get("requires-python"),
            "dependencies": project.get("dependencies", []),
            "optional_dependencies": project.get("optional-dependencies", {}),
        }

    def _module_available(self, module_name: str) -> bool:
        aliases = _IMPORT_ALIASES.get(module_name, (module_name,))
        return any(self._module_exists_provider(alias) for alias in aliases)

    def _matching_branch_stage(self, stages: list[StageSnapshot], stage_key: StageKey) -> StageSnapshot | None:
        for stage in stages:
            if stage.stage_key is stage_key:
                return stage
        return None

    def _primary_blocker(self, blockers: PreflightBlockersByCategory) -> PreflightBlocker | None:
        grouped = {
            PreflightBlockerCategory.RUNTIME: blockers.runtime,
            PreflightBlockerCategory.DEPENDENCY: blockers.dependency,
            PreflightBlockerCategory.ARTIFACT: blockers.artifact,
            PreflightBlockerCategory.STATE: blockers.state,
            PreflightBlockerCategory.RECOVERY: blockers.recovery,
        }
        for category in _CATEGORY_ORDER:
            category_blockers = grouped[category]
            if category_blockers:
                return category_blockers[0]
        return None

    def _add_blocker(
        self,
        blockers: PreflightBlockersByCategory,
        category: PreflightBlockerCategory,
        reason: str,
        repair_action: str,
    ) -> None:
        blocker = PreflightBlocker(
            category=category,
            reason=reason,
            repair_action=repair_action,
        )
        if category is PreflightBlockerCategory.RUNTIME:
            blockers.runtime.append(blocker)
        elif category is PreflightBlockerCategory.DEPENDENCY:
            blockers.dependency.append(blocker)
        elif category is PreflightBlockerCategory.ARTIFACT:
            blockers.artifact.append(blocker)
        elif category is PreflightBlockerCategory.STATE:
            blockers.state.append(blocker)
        else:
            blockers.recovery.append(blocker)

    def _normalize_dependency_names(self, values: Any) -> set[str]:
        normalized: set[str] = set()
        if not isinstance(values, list):
            return normalized
        for value in values:
            if not isinstance(value, str):
                continue
            match = re.match(r"([A-Za-z0-9_.-]+)", value.strip())
            if match is not None:
                normalized.add(match.group(1).lower())
        return normalized

    def _parse_minimum_python_version(self, specifier: str) -> tuple[int, int, int] | None:
        match = re.search(r">=\s*(\d+)(?:\.(\d+))?(?:\.(\d+))?", specifier)
        if match is None:
            return None
        major = int(match.group(1))
        minor = 0 if match.group(2) is None else int(match.group(2))
        patch = 0 if match.group(3) is None else int(match.group(3))
        return (major, minor, patch)

    @staticmethod
    def _default_python_version() -> tuple[int, int, int]:
        import sys

        return (sys.version_info.major, sys.version_info.minor, sys.version_info.micro)

    @staticmethod
    def _default_command_exists(command_name: str) -> bool:
        import shutil

        return shutil.which(command_name) is not None

    @staticmethod
    def _default_module_exists(module_name: str) -> bool:
        import importlib.util

        return importlib.util.find_spec(module_name) is not None


__all__ = ["PreflightService"]
