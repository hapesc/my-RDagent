from __future__ import annotations

from pathlib import Path

from v3.devtools.skill_install import install_agent_skills, resolve_bundle_root, resolve_target_root


def _make_repo(tmp_path: Path) -> Path:
    repo_root = tmp_path / "repo"
    (repo_root / "skills").mkdir(parents=True)
    (repo_root / "v3").mkdir()
    (repo_root / "scripts").mkdir()
    (repo_root / "pyproject.toml").write_text("[project]\nname='fixture'\n", encoding="utf-8")
    (repo_root / "uv.lock").write_text("version = 1\n", encoding="utf-8")
    (repo_root / "README.md").write_text("# fixture\n", encoding="utf-8")
    (repo_root / "v3" / "__init__.py").write_text("", encoding="utf-8")
    (repo_root / "scripts" / "install_agent_skills.py").write_text("#!/usr/bin/env python3\n", encoding="utf-8")

    for skill_name in ("alpha", "beta"):
        skill_dir = repo_root / "skills" / skill_name
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(f"# {skill_name}\n", encoding="utf-8")
        (skill_dir / "notes.txt").write_text(f"{skill_name}\n", encoding="utf-8")

    return repo_root


def test_link_install_creates_runtime_bundle_and_generated_skills(tmp_path: Path) -> None:
    repo_root = _make_repo(tmp_path)

    records = install_agent_skills(runtime="all", scope="local", mode="link", repo_root=repo_root)

    assert len(records) == 4
    for runtime in ("codex", "claude"):
        bundle_root = resolve_bundle_root(runtime, "local", repo_root=repo_root)
        assert bundle_root.is_dir()
        assert (bundle_root / "pyproject.toml").is_symlink()
        assert (bundle_root / "v3").is_symlink()
        assert (bundle_root / ".rdagent-runtime-install.json").is_file()

        target_root = resolve_target_root(runtime, "local", repo_root=repo_root)
        assert target_root.is_dir()
        for skill_name in ("alpha", "beta"):
            destination = target_root / skill_name
            assert destination.is_dir()
            assert not destination.is_symlink()
            assert (destination / ".rdagent-skill-install.json").is_file()
            assert (destination / "notes.txt").is_symlink()
            text = (destination / "SKILL.md").read_text(encoding="utf-8")
            assert f"# {skill_name}\n" in text
            assert str(bundle_root) in text
            assert "uv run rdagent-v3-tool list" in text


def test_rerun_is_idempotent(tmp_path: Path) -> None:
    repo_root = _make_repo(tmp_path)

    install_agent_skills(runtime="codex", scope="local", mode="link", repo_root=repo_root)
    install_agent_skills(runtime="codex", scope="local", mode="link", repo_root=repo_root)

    target_root = resolve_target_root("codex", "local", repo_root=repo_root)
    assert sorted(path.name for path in target_root.iterdir()) == ["alpha", "beta"]
    assert all((target_root / skill_name).is_dir() for skill_name in ("alpha", "beta"))
    assert all(
        ((target_root / skill_name) / ".rdagent-skill-install.json").is_file() for skill_name in ("alpha", "beta")
    )


def test_broken_link_is_repaired(tmp_path: Path) -> None:
    repo_root = _make_repo(tmp_path)

    install_agent_skills(runtime="codex", scope="local", mode="link", repo_root=repo_root)
    notes_link = resolve_target_root("codex", "local", repo_root=repo_root) / "alpha" / "notes.txt"
    notes_link.unlink()
    notes_link.symlink_to(repo_root / "skills" / "missing-alpha" / "notes.txt")
    assert notes_link.is_symlink()
    assert not notes_link.exists()

    install_agent_skills(runtime="codex", scope="local", mode="link", repo_root=repo_root)

    assert notes_link.is_symlink()
    assert notes_link.resolve() == repo_root / "skills" / "alpha" / "notes.txt"


def test_copy_mode_creates_real_files(tmp_path: Path) -> None:
    repo_root = _make_repo(tmp_path)

    records = install_agent_skills(runtime="claude", scope="local", mode="copy", repo_root=repo_root)

    copied = [record for record in records if record.action == "copied"]
    assert len(copied) == 2

    bundle_root = resolve_bundle_root("claude", "local", repo_root=repo_root)
    assert bundle_root.is_dir()
    assert not (bundle_root / "v3").is_symlink()

    target_root = resolve_target_root("claude", "local", repo_root=repo_root)
    for skill_name in ("alpha", "beta"):
        destination = target_root / skill_name
        assert destination.is_dir()
        assert not destination.is_symlink()
        assert not (destination / "notes.txt").is_symlink()
        text = (destination / "SKILL.md").read_text(encoding="utf-8")
        assert f"# {skill_name}\n" in text
        assert str(bundle_root) in text


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
    assert (target_root / "beta").is_dir()
    assert ((target_root / "beta") / ".rdagent-skill-install.json").is_file()
