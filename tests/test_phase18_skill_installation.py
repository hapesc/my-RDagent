from __future__ import annotations

from pathlib import Path

from v3.devtools.skill_install import install_agent_skills, resolve_target_root


def _make_repo(tmp_path: Path) -> Path:
    repo_root = tmp_path / "repo"
    (repo_root / "skills").mkdir(parents=True)
    (repo_root / "pyproject.toml").write_text("[project]\nname='fixture'\n", encoding="utf-8")

    for skill_name in ("alpha", "beta"):
        skill_dir = repo_root / "skills" / skill_name
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(f"# {skill_name}\n", encoding="utf-8")
        (skill_dir / "notes.txt").write_text(f"{skill_name}\n", encoding="utf-8")

    return repo_root


def test_symlink_install(tmp_path: Path) -> None:
    repo_root = _make_repo(tmp_path)

    records = install_agent_skills(runtime="all", scope="local", mode="link", repo_root=repo_root)

    assert len(records) == 4
    for runtime in ("codex", "claude"):
        target_root = resolve_target_root(runtime, "local", repo_root=repo_root)
        assert target_root.is_dir()
        for skill_name in ("alpha", "beta"):
            destination = target_root / skill_name
            assert destination.is_symlink()
            assert destination.resolve() == repo_root / "skills" / skill_name


def test_rerun_is_idempotent(tmp_path: Path) -> None:
    repo_root = _make_repo(tmp_path)

    install_agent_skills(runtime="codex", scope="local", mode="link", repo_root=repo_root)
    install_agent_skills(runtime="codex", scope="local", mode="link", repo_root=repo_root)

    target_root = resolve_target_root("codex", "local", repo_root=repo_root)
    assert sorted(path.name for path in target_root.iterdir()) == ["alpha", "beta"]
    assert all((target_root / skill_name).is_symlink() for skill_name in ("alpha", "beta"))


def test_broken_link_is_repaired(tmp_path: Path) -> None:
    repo_root = _make_repo(tmp_path)

    install_agent_skills(runtime="codex", scope="local", mode="link", repo_root=repo_root)
    destination = resolve_target_root("codex", "local", repo_root=repo_root) / "alpha"
    destination.unlink()
    destination.symlink_to(repo_root / "skills" / "missing-alpha", target_is_directory=True)
    assert destination.is_symlink()
    assert not destination.exists()

    install_agent_skills(runtime="codex", scope="local", mode="link", repo_root=repo_root)

    assert destination.is_symlink()
    assert destination.resolve() == repo_root / "skills" / "alpha"


def test_copy_mode_creates_real_files(tmp_path: Path) -> None:
    repo_root = _make_repo(tmp_path)

    records = install_agent_skills(runtime="claude", scope="local", mode="copy", repo_root=repo_root)

    copied = [record for record in records if record.action == "copied"]
    assert len(copied) == 2

    target_root = resolve_target_root("claude", "local", repo_root=repo_root)
    for skill_name in ("alpha", "beta"):
        destination = target_root / skill_name
        assert destination.is_dir()
        assert not destination.is_symlink()
        assert (destination / "SKILL.md").read_text(encoding="utf-8") == f"# {skill_name}\n"


def test_unrelated_targets_are_preserved(tmp_path: Path) -> None:
    repo_root = _make_repo(tmp_path)
    target_root = resolve_target_root("codex", "local", repo_root=repo_root)
    preserved_target = target_root / "alpha"
    preserved_target.mkdir(parents=True)
    (preserved_target / "custom.txt").write_text("keep me\n", encoding="utf-8")

    records = install_agent_skills(runtime="codex", scope="local", mode="link", repo_root=repo_root)

    actions = {record.skill_name: record.action for record in records}
    assert actions == {"alpha": "preserved", "beta": "linked"}
    assert preserved_target.is_dir()
    assert not preserved_target.is_symlink()
    assert (preserved_target / "custom.txt").read_text(encoding="utf-8") == "keep me\n"
    assert (target_root / "beta").is_symlink()
