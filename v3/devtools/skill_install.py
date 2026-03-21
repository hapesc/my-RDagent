"""Install repo-local skills into Claude and Codex skill roots."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import shutil

MANAGED_MARKER = ".rdagent-skill-install.json"
RUNTIMES = ("codex", "claude")
SCOPES = ("local", "global")
MODES = ("link", "copy")
TARGET_ROOTS = {
    ("codex", "local"): Path(".codex/skills"),
    ("claude", "local"): Path(".claude/skills"),
    ("codex", "global"): Path("~/.codex/skills"),
    ("claude", "global"): Path("~/.claude/skills"),
}


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
    skill_dirs = [
        child
        for child in sorted(skills_root.iterdir())
        if child.is_dir() and (child / "SKILL.md").is_file()
    ]
    return skill_dirs


def resolve_target_root(
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
    target = TARGET_ROOTS[(runtime, scope)]
    if scope == "local":
        return root / target
    return Path(home or Path.home()) / target.relative_to("~")


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
            target_root = resolve_target_root(runtime_name, scope_name, repo_root=root, home=home)
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
                    )
                )

    return records


def _expand_selection(value: str, allowed: tuple[str, ...], label: str) -> tuple[str, ...]:
    if value == "all":
        return allowed
    if value not in allowed:
        raise ValueError(f"unsupported {label}: {value}")
    return (value,)


def _install_skill_dir(
    *,
    runtime: str,
    scope: str,
    mode: str,
    source_dir: Path,
    destination: Path,
) -> InstallRecord:
    action = "preserved"
    if destination.exists() or destination.is_symlink():
        if _is_managed_target(destination):
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

    if mode == "link":
        destination.symlink_to(source_dir, target_is_directory=True)
        action = "linked"
    elif mode == "copy":
        shutil.copytree(
            source_dir,
            destination,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
        _write_marker(destination, source_dir)
        action = "copied"
    else:
        raise ValueError(f"unsupported mode: {mode}")

    return InstallRecord(
        runtime=runtime,
        scope=scope,
        mode=mode,
        skill_name=source_dir.name,
        source=source_dir,
        destination=destination,
        action=action,
    )


def _is_managed_target(path: Path) -> bool:
    if path.is_symlink():
        return True
    return path.is_dir() and (path / MANAGED_MARKER).is_file()


def _remove_target(path: Path) -> None:
    if path.is_symlink():
        path.unlink()
        return
    if path.is_dir():
        shutil.rmtree(path)
        return
    path.unlink()


def _write_marker(destination: Path, source_dir: Path) -> None:
    marker = destination / MANAGED_MARKER
    marker.write_text(
        json.dumps(
            {
                "managed_by": "v3.devtools.skill_install",
                "source": str(source_dir),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
