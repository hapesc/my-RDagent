"""Install standalone V3 runtime bundles and generated skills for Claude/Codex."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import shutil

SKILL_MANAGED_MARKER = ".rdagent-skill-install.json"
RUNTIME_MANAGED_MARKER = ".rdagent-runtime-install.json"
RUNTIME_BUNDLE_NAME = "rdagent-v3"
RUNTIMES = ("codex", "claude")
SCOPES = ("local", "global")
MODES = ("link", "copy")
CONFIG_ROOTS = {
    ("codex", "local"): Path(".codex"),
    ("claude", "local"): Path(".claude"),
    ("codex", "global"): Path("~/.codex"),
    ("claude", "global"): Path("~/.claude"),
}
RUNTIME_BUNDLE_PATHS = (
    Path("pyproject.toml"),
    Path("uv.lock"),
    Path("README.md"),
    Path("scripts"),
    Path("skills"),
    Path("v3"),
)


@dataclass(frozen=True)
class InstallRecord:
    runtime: str
    scope: str
    mode: str
    skill_name: str
    source: Path
    destination: Path
    action: str


def discover_repo_root(start: Path | None = None) -> Path:
    candidate = (start or Path(__file__)).resolve()
    search = candidate if candidate.is_dir() else candidate.parent
    for directory in (search, *search.parents):
        if (directory / "pyproject.toml").is_file() and (directory / "skills").is_dir():
            return directory
    raise FileNotFoundError("could not locate repo root containing pyproject.toml and skills/")


def discover_skill_dirs(repo_root: Path | None = None) -> list[Path]:
    root = discover_repo_root(repo_root)
    skills_root = root / "skills"
    return [
        child
        for child in sorted(skills_root.iterdir())
        if child.is_dir() and (child / "SKILL.md").is_file()
    ]


def resolve_config_root(
    runtime: str,
    scope: str,
    repo_root: Path | None = None,
    home: Path | None = None,
) -> Path:
    if runtime not in RUNTIMES:
        raise ValueError(f"unsupported runtime: {runtime}")
    if scope not in SCOPES:
        raise ValueError(f"unsupported scope: {scope}")

    root = discover_repo_root(repo_root)
    target = CONFIG_ROOTS[(runtime, scope)]
    if scope == "local":
        return root / target
    return Path(home or Path.home()) / target.relative_to("~")


def resolve_target_root(
    runtime: str,
    scope: str,
    repo_root: Path | None = None,
    home: Path | None = None,
) -> Path:
    return resolve_config_root(runtime, scope, repo_root=repo_root, home=home) / "skills"


def resolve_bundle_root(
    runtime: str,
    scope: str,
    repo_root: Path | None = None,
    home: Path | None = None,
) -> Path:
    return resolve_config_root(runtime, scope, repo_root=repo_root, home=home) / RUNTIME_BUNDLE_NAME


def install_agent_skills(
    *,
    runtime: str = "all",
    scope: str = "local",
    mode: str = "link",
    repo_root: Path | None = None,
    home: Path | None = None,
) -> list[InstallRecord]:
    if mode not in MODES:
        raise ValueError(f"unsupported mode: {mode}")

    root = discover_repo_root(repo_root)
    runtimes = _expand_selection(runtime, RUNTIMES, "runtime")
    scopes = _expand_selection(scope, SCOPES, "scope")
    skill_dirs = discover_skill_dirs(root)
    records: list[InstallRecord] = []

    for runtime_name in runtimes:
        for scope_name in scopes:
            config_root = resolve_config_root(runtime_name, scope_name, repo_root=root, home=home)
            bundle_root = config_root / RUNTIME_BUNDLE_NAME
            target_root = config_root / "skills"
            _install_runtime_bundle(
                runtime=runtime_name,
                scope=scope_name,
                mode=mode,
                repo_root=root,
                bundle_root=bundle_root,
            )
            target_root.mkdir(parents=True, exist_ok=True)
            for source_dir in skill_dirs:
                destination = target_root / source_dir.name
                records.append(
                    _install_skill_dir(
                        runtime=runtime_name,
                        scope=scope_name,
                        mode=mode,
                        source_dir=source_dir,
                        destination=destination,
                        bundle_root=bundle_root,
                    )
                )

    return records


def _expand_selection(value: str, allowed: tuple[str, ...], label: str) -> tuple[str, ...]:
    if value == "all":
        return allowed
    if value not in allowed:
        raise ValueError(f"unsupported {label}: {value}")
    return (value,)


def _install_runtime_bundle(
    *,
    runtime: str,
    scope: str,
    mode: str,
    repo_root: Path,
    bundle_root: Path,
) -> None:
    if bundle_root.exists() or bundle_root.is_symlink():
        if _is_managed_runtime_target(bundle_root):
            _remove_target(bundle_root)
        else:
            raise ValueError(f"refusing to overwrite unmanaged runtime bundle: {bundle_root}")

    bundle_root.mkdir(parents=True, exist_ok=True)
    for relative_path in RUNTIME_BUNDLE_PATHS:
        source = repo_root / relative_path
        destination = bundle_root / relative_path
        _install_bundle_path(source=source, destination=destination, mode=mode)
    _write_runtime_marker(
        destination=bundle_root,
        repo_root=repo_root,
        runtime=runtime,
        scope=scope,
        mode=mode,
    )


def _install_bundle_path(*, source: Path, destination: Path, mode: str) -> None:
    if mode == "link":
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.symlink_to(source, target_is_directory=source.is_dir())
        return
    if source.is_dir():
        shutil.copytree(
            source,
            destination,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def _install_skill_dir(
    *,
    runtime: str,
    scope: str,
    mode: str,
    source_dir: Path,
    destination: Path,
    bundle_root: Path,
) -> InstallRecord:
    action = "preserved"
    if destination.exists() or destination.is_symlink():
        if _is_managed_skill_target(destination):
            _remove_target(destination)
        else:
            return InstallRecord(
                runtime=runtime,
                scope=scope,
                mode=mode,
                skill_name=source_dir.name,
                source=source_dir,
                destination=destination,
                action=action,
            )

    destination.mkdir(parents=True, exist_ok=True)
    _install_skill_support_files(source_dir=source_dir, destination=destination, mode=mode)
    (destination / "SKILL.md").write_text(
        _render_installed_skill(
            source_text=(source_dir / "SKILL.md").read_text(encoding="utf-8"),
            bundle_root=bundle_root,
            source_dir=source_dir,
        ),
        encoding="utf-8",
    )
    _write_skill_marker(
        destination=destination,
        source_dir=source_dir,
        bundle_root=bundle_root,
        runtime=runtime,
        scope=scope,
        mode=mode,
    )
    action = "linked" if mode == "link" else "copied"

    return InstallRecord(
        runtime=runtime,
        scope=scope,
        mode=mode,
        skill_name=source_dir.name,
        source=source_dir,
        destination=destination,
        action=action,
    )


def _install_skill_support_files(*, source_dir: Path, destination: Path, mode: str) -> None:
    for child in sorted(source_dir.iterdir()):
        if child.name == "SKILL.md":
            continue
        target = destination / child.name
        if mode == "link":
            target.symlink_to(child, target_is_directory=child.is_dir())
            continue
        if child.is_dir():
            shutil.copytree(
                child,
                target,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            )
            continue
        shutil.copy2(child, target)


def _render_installed_skill(*, source_text: str, bundle_root: Path, source_dir: Path) -> str:
    suffix = f"""

## Installed runtime bundle

- This installed skill is bound to the standalone V3 runtime bundle at `{bundle_root}`.
- Run direct V3 CLI tools from that bundle root, not from the caller repo unless the caller repo is this bundle.
- The canonical direct-tool path is:
  - `cd {bundle_root}`
  - `uv run rdagent-v3-tool list`
  - `uv run rdagent-v3-tool describe <tool>`
- Keep state inspection scoped to the current working repo's canonical V3 state or an explicitly provided state root.
- If the current working repo has no canonical V3 state, do not scan other repos or `HOME`; stay on the fresh-start or minimum-contract path.
- Relative resources for this installed skill still resolve inside `{bundle_root / "skills" / source_dir.name}`.
"""
    return source_text.rstrip() + suffix


def _is_managed_skill_target(path: Path) -> bool:
    return path.is_dir() and (path / SKILL_MANAGED_MARKER).is_file()


def _is_managed_runtime_target(path: Path) -> bool:
    return path.is_dir() and (path / RUNTIME_MANAGED_MARKER).is_file()


def _remove_target(path: Path) -> None:
    if path.is_symlink():
        path.unlink()
        return
    if path.is_dir():
        shutil.rmtree(path)
        return
    path.unlink()


def _write_skill_marker(
    *,
    destination: Path,
    source_dir: Path,
    bundle_root: Path,
    runtime: str,
    scope: str,
    mode: str,
) -> None:
    marker = destination / SKILL_MANAGED_MARKER
    marker.write_text(
        json.dumps(
            {
                "managed_by": "v3.devtools.skill_install",
                "source": str(source_dir),
                "bundle_root": str(bundle_root),
                "runtime": runtime,
                "scope": scope,
                "mode": mode,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _write_runtime_marker(
    *,
    destination: Path,
    repo_root: Path,
    runtime: str,
    scope: str,
    mode: str,
) -> None:
    marker = destination / RUNTIME_MANAGED_MARKER
    marker.write_text(
        json.dumps(
            {
                "managed_by": "v3.devtools.skill_install",
                "repo_root": str(repo_root),
                "runtime": runtime,
                "scope": scope,
                "mode": mode,
                "bundle_paths": [str(path) for path in RUNTIME_BUNDLE_PATHS],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
