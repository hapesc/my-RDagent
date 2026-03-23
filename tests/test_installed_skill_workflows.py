"""Gate 2: Verify installed skills resolve their workflows/ and references/ directories."""

from __future__ import annotations

import tempfile
from pathlib import Path

from v3.devtools.skill_install import discover_repo_root, install_agent_skills


def test_installed_skills_resolve_workflows_and_references() -> None:
    repo_root = discover_repo_root()

    with tempfile.TemporaryDirectory() as tmp:
        for runtime in ("claude", "codex"):
            records = install_agent_skills(
                runtime=runtime,
                scope="local",
                mode="link",
                repo_root=repo_root,
                home=Path(tmp),
            )
            for record in records:
                if record.action != "linked":
                    continue
                dest = record.destination
                skill_source = repo_root / "skills" / record.skill_name

                # Verify workflows/ dir was symlinked if source has one
                if (skill_source / "workflows").is_dir():
                    assert (dest / "workflows").is_symlink() or (
                        dest / "workflows"
                    ).is_dir(), (
                        f"workflows/ not installed for {record.skill_name} ({runtime})"
                    )
                    for wf in sorted((skill_source / "workflows").iterdir()):
                        assert (dest / "workflows" / wf.name).exists(), (
                            f"Missing installed workflow: {wf.name} for {record.skill_name} ({runtime})"
                        )

                # Verify references/ dir was symlinked if source has one
                if (skill_source / "references").is_dir():
                    assert (dest / "references").is_symlink() or (
                        dest / "references"
                    ).is_dir(), (
                        f"references/ not installed for {record.skill_name} ({runtime})"
                    )

                # Verify SKILL.md still has installed runtime bundle section
                text = (dest / "SKILL.md").read_text()
                assert "Installed runtime bundle" in text, (
                    f"Missing runtime bundle section for {record.skill_name} ({runtime})"
                )
