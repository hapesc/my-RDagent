from __future__ import annotations

from pathlib import Path

from rd_agent.devtools.skill_install import install_agent_skills, resolve_bundle_root, resolve_target_root


def _make_repo(tmp_path: Path) -> Path:
    repo_root = tmp_path / "repo"
    (repo_root / "skills").mkdir(parents=True)
    (repo_root / "rd_agent").mkdir()
    (repo_root / "scripts").mkdir()
    (repo_root / "pyproject.toml").write_text("[project]\nname='fixture'\n", encoding="utf-8")
    (repo_root / "uv.lock").write_text("version = 1\n", encoding="utf-8")
    (repo_root / "README.md").write_text("# fixture\n", encoding="utf-8")
    (repo_root / "rd_agent" / "__init__.py").write_text("", encoding="utf-8")
    (repo_root / "scripts" / "install_agent_skills.py").write_text("#!/usr/bin/env python3\n", encoding="utf-8")

    for skill_name in ("alpha", "beta"):
        skill_dir = repo_root / "skills" / skill_name
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(f"# {skill_name}\n", encoding="utf-8")
        (skill_dir / "notes.txt").write_text(f"{skill_name}\n", encoding="utf-8")

    return repo_root


def test_copy_install_creates_runtime_bundle_and_generated_skills(tmp_path: Path) -> None:
    repo_root = _make_repo(tmp_path)

    records = install_agent_skills(runtime="all", scope="local", repo_root=repo_root)

    assert len(records) == 4
    for runtime in ("codex", "claude"):
        bundle_root = resolve_bundle_root(runtime, "local", repo_root=repo_root)
        assert bundle_root.is_dir()
        assert (bundle_root / "pyproject.toml").is_file()
        assert not (bundle_root / "pyproject.toml").is_symlink()
        assert (bundle_root / "rd_agent").is_dir()
        assert not (bundle_root / "rd_agent").is_symlink()
        assert (bundle_root / ".rdagent-runtime-install.json").is_file()

        target_root = resolve_target_root(runtime, "local", repo_root=repo_root)
        assert target_root.is_dir()
        for skill_name in ("alpha", "beta"):
            destination = target_root / skill_name
            assert destination.is_dir()
            assert not destination.is_symlink()
            assert (destination / ".rdagent-skill-install.json").is_file()
            assert (destination / "notes.txt").is_file()
            assert not (destination / "notes.txt").is_symlink()
            text = (destination / "SKILL.md").read_text(encoding="utf-8")
            assert f"# {skill_name}\n" in text
            assert str(bundle_root) in text
            assert "uv run" in text


def test_rerun_is_idempotent(tmp_path: Path) -> None:
    repo_root = _make_repo(tmp_path)

    install_agent_skills(runtime="codex", scope="local", repo_root=repo_root)
    install_agent_skills(runtime="codex", scope="local", repo_root=repo_root)

    target_root = resolve_target_root("codex", "local", repo_root=repo_root)
    assert sorted(path.name for path in target_root.iterdir()) == ["alpha", "beta"]
    assert all((target_root / skill_name).is_dir() for skill_name in ("alpha", "beta"))
    assert all(
        ((target_root / skill_name) / ".rdagent-skill-install.json").is_file() for skill_name in ("alpha", "beta")
    )


def test_copied_files_are_independent(tmp_path: Path) -> None:
    repo_root = _make_repo(tmp_path)

    install_agent_skills(runtime="codex", scope="local", repo_root=repo_root)

    target_root = resolve_target_root("codex", "local", repo_root=repo_root)
    installed_notes = target_root / "alpha" / "notes.txt"
    assert installed_notes.is_file()
    assert not installed_notes.is_symlink()

    # Modify source — installed copy should be unaffected
    (repo_root / "skills" / "alpha" / "notes.txt").write_text("changed\n", encoding="utf-8")
    assert installed_notes.read_text(encoding="utf-8") == "alpha\n"


def test_unrelated_targets_are_preserved(tmp_path: Path) -> None:
    repo_root = _make_repo(tmp_path)
    target_root = resolve_target_root("codex", "local", repo_root=repo_root)
    preserved_target = target_root / "alpha"
    preserved_target.mkdir(parents=True)
    (preserved_target / "custom.txt").write_text("keep me\n", encoding="utf-8")

    records = install_agent_skills(runtime="codex", scope="local", repo_root=repo_root)

    actions = {record.skill_name: record.action for record in records}
    assert actions == {"alpha": "preserved", "beta": "copied"}
    assert preserved_target.is_dir()
    assert not preserved_target.is_symlink()
    assert (preserved_target / "custom.txt").read_text(encoding="utf-8") == "keep me\n"
    assert (target_root / "beta").is_dir()
    assert ((target_root / "beta") / ".rdagent-skill-install.json").is_file()
