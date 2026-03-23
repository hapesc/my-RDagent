# Phase 18: Standalone Packaging and Planning Autonomy - Research

**Researched:** 2026-03-21
**Domain:** standalone packaging, agent skill exposure, and planning continuity
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
### Skill installation and exposure
- `skills/` remains the canonical source of truth for repo-local skill
  packages.
- Phase 18 should add a repo-local installer/linker workflow that exposes these
  skills into agent-recognized roots instead of expecting agents to scan the
  git repo directly.
- The supported targets are both Codex and Claude Code.
- The supported installation locations are both global and local:
  `~/.codex/skills/`, `~/.claude/skills/`, `./.codex/skills/`, and
  `./.claude/skills/`.
- The default installation mode is symbolic linking, not copying.
- A copy-style fallback may exist only as a compatibility backstop, not as the
  primary workflow.
- Skill installation must not move or duplicate CLI tools.

### CLI runtime contract
- CLI tools remain repo-environment-owned rather than agent-root-owned.
- The standard usage model for `rdagent-v3-tool` is from the cloned repo's
  environment, not as a globally installed shell command contract.
- Phase 18 should preserve the existing `rdagent-v3-tool` console entrypoint
  while documenting repo-environment execution as the canonical operator path.
- Skill installation and CLI execution must be documented as two separate
  flows: skill discovery for agents, tool execution from the repo environment
  for users and agents.

### Verification posture
- Phase 18 should document and implement two verification levels: `Quick` and
  `Full`.
- `Quick` should prove the standalone repo is usable with minimal setup.
- `Full` should prove public-surface integrity, continuity integrity, and
  broader regression health before calling the repo hardened.
- Verification guidance should match the new install/runtime split: skills can
  be linked into agent roots, but CLI validation remains repo-environment
  based.

### Public vs internal documentation boundary
- `README.md` is a public user-facing document and must not retain session
  continuation, planning recovery, or developer-only workflow sections.
- README should describe:
  what the repo ships, how to set up the repo environment, how to expose skills
  to agents, how to run CLI tools, and how to run quick/full validation.
- README should not describe:
  `.planning/` reading order, current milestone recovery, or internal GSD
  operator instructions.
- Internal continuity for standalone planning should move to
  `.planning/STATE.md`, which becomes the canonical internal resume entrypoint.

### Historical cleanup and continuity
- Phase 18 should thoroughly clean stale upstream residue from active docs,
  rather than merely deprioritizing it.
- Active docs must not point to removed `docs/context/*` paths, stale absolute
  machine-local paths, or upstream-worktree continuation steps.
- Historical artifacts may remain as archives, but they must no longer present
  themselves as the current source of truth.
- The standalone repo's `.planning/` tree should be sufficient for future GSD
  work without requiring upstream references.

### Claude's Discretion
- The exact installer command name, script location, and argument syntax may be
  chosen during planning as long as the runtime/location choices above are
  explicit and decision-complete.
- The exact composition of the `Quick` and `Full` verification commands may be
  chosen during planning as long as they preserve the locked two-tier posture.
- Whether compatibility copy mode is exposed as a flag, secondary command, or
  repair path is flexible as long as symlink install remains the default.

### Deferred Ideas (OUT OF SCOPE)
- Shipping additional standalone console commands beyond `rdagent-v3-tool`
  belongs to a later phase if the product surface needs more direct CLI entry
  points.
- Automatic skill discovery/runtime support that removes the need for explicit
  install/link steps belongs to a later phase.
- Any broader packaging or distribution strategy beyond self-contained repo use
  and agent skill exposure belongs to a later phase.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| STANDALONE-01 | Developer can install and validate `my-RDagent-V3` as a self-contained repository without legacy `app`, `core`, or `exploration_manager` dependencies. | Keep the repo install flow on `uv sync --extra test`, preserve `rdagent-v3-tool` as the only public console script, and add a repo-local skill installer/linker that targets Claude/Codex roots without introducing legacy imports or a second product surface. |
| STANDALONE-02 | Developer can continue GSD planning and milestone work inside the standalone repo using only its local `.planning/` artifacts. | Move the internal continuity contract into `.planning/STATE.md`, remove planning-resume content from README, and add doc regressions that forbid stale `docs/context/*` and absolute-path startup instructions in active guidance. |
</phase_requirements>

## Summary

Phase 18 is a packaging-and-truth phase, not a runtime-expansion phase. The
repo already has the essential pieces: repo-local `skills/`, a single public
CLI script in `pyproject.toml`, focused public-surface tests, and a `.planning/`
tree that already owns roadmap and state truth. The missing work is to connect
those pieces coherently: expose skills into agent-recognized roots, keep CLI
execution repo-environment-owned, and stop mixing internal planning continuity
into public README copy.

The current build boundary is a strong planning signal. `pyproject.toml` only
packages `v3` and only exports `rdagent-v3-tool`, which means adding another
public console command would expand the product surface. The cleaner approach
is a repo-local installer/linker workflow for skills plus regression tests that
lock the README/STATE/HANDOFF responsibilities. The import-linter contracts and
passing CLI/doc regressions show the repo is already stable enough to harden
without new third-party dependencies.

**Primary recommendation:** split Phase 18 into four plan slices: implement a
repo-local skill installer/linker, rewrite README around public install/runtime
guidance only, move continuity truth into `.planning/STATE.md` while demoting
stale handoff guidance, and add Phase 18 regression tests plus quick/full
verification commands.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | `>=3.11` | runtime for installer logic and validation scripts | already fixed by `pyproject.toml` and sufficient for symlink/path operations |
| `pathlib` / `os` / `shutil` | stdlib | create, repair, and inspect local/global skill links | no extra dependency is needed for filesystem-based skill exposure |
| `argparse` | stdlib | installer CLI argument parsing | matches the existing `v3.entry.tool_cli` pattern and keeps the surface minimal |
| `hatchling` | repo build backend | keep current package build unchanged | Phase 18 should preserve the existing build contract rather than switch packaging systems |
| Repo-local `skills/` tree | repo-local | canonical skill source | already exists and should remain the only truth source for skill content |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pytest` | `>=7.4.0` | regression tests for installer flow, docs, and continuity | for all new Phase 18 behavioral and doc-surface assertions |
| `import-linter` | `>=2.3,<3.0` | boundary gate against legacy runtime imports | at full phase gate to prove no new legacy coupling leaked in |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| repo-local installer/linker | another public `[project.scripts]` console entrypoint | expands the public surface and blurs the repo-env vs agent-root boundary |
| symlink-first install | copy-first install | copy mode is more portable but becomes stale after repo updates; better as fallback only |
| `.planning/STATE.md` as continuity home | README continuation section | README is public-facing and should not leak internal maintenance workflow |

**Installation:**
```bash
uv sync --extra test
```

## Architecture Patterns

### Recommended Project Structure
```text
scripts/
└── install_agent_skills.py      # thin repo-local wrapper, not a new public product command

v3/
└── devtools/
    └── skill_install.py         # importable stdlib-heavy link/copy logic for tests

tests/
├── test_phase18_skill_installation.py
└── test_phase18_planning_continuity.py
```

### Pattern 1: Canonical-Source Linker
**What:** keep `skills/` untouched and expose it into Claude/Codex skill roots
through symlinks created from a repo-local installer.
**When to use:** for `~/.codex/skills`, `~/.claude/skills`, `./.codex/skills`,
and `./.claude/skills`.
**Why:** this preserves one source of truth and lets repo updates flow through
without re-copying skill packages.

### Pattern 2: Public CLI Surface Stays Flat
**What:** keep `rdagent-v3-tool` as the only documented public console script
and do not add a second public operator command for skill installation.
**When to use:** always for this phase unless a later requirement explicitly
promotes installer behavior to the public product surface.
**Implementation seam:** `pyproject.toml` currently exposes only
`rdagent-v3-tool`, and `v3/entry/tool_cli.py` is a minimal `argparse` CLI.

### Pattern 3: Public Docs vs Internal Continuity Split
**What:** README explains install/runtime/verification for end users; internal
continuity moves into `.planning/STATE.md`.
**When to use:** for all Phase 18 doc edits.
**Why:** the current README mixes public surface documentation with
session-recovery instructions, which violates the locked boundary from
`18-CONTEXT.md`.

### Pattern 4: Continuity by Regression, Not Memory
**What:** add direct file-reading tests that assert:
- README contains public install/runtime guidance
- README does not contain "Continue This Session"
- `.planning/STATE.md` points to the next internal action
- active continuity docs do not reference `docs/context/*` or stale absolute
  startup paths
**When to use:** for STANDALONE-02 and as part of the quick gate.

### Likely Plan Slices
1. Add the repo-local skill installer/linker and its tests.
2. Rewrite README around public repo setup, agent skill exposure, repo-env CLI,
   and quick/full verification.
3. Rewrite `.planning/STATE.md` into the canonical continuity entrypoint and
   demote or archive stale handoff guidance.
4. Add/update regression tests and verification docs so Phase 18 is locked.

### Anti-Patterns to Avoid
- **Public installer command creep:** do not turn the skill installer into a
  second public product command unless requirements change.
- **Copy-first installs:** copying skills into agent roots by default will make
  the installed set drift from repo truth after updates.
- **README as internal runbook:** Phase 18 fails if public docs still carry
  planning-resume steps.
- **Silent stale links:** installer behavior must detect existing/broken links
  and repair or replace them deterministically.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| agent skill discovery | a custom registry/database/service | filesystem links in recognized skill roots | the agents already discover `SKILL.md` from known directories; no second discovery system is needed |
| packaging overhaul | a new build backend or distribution story | current `hatchling` + repo-local workflow | the requirement is self-contained repo usability, not a new publish/install channel |
| continuity state | ad hoc README notes or handoff prose | `.planning/STATE.md` as the canonical resume artifact | one internal truth source is easier to test and maintain |

**Key insight:** Phase 18 should harden the boundaries between existing layers,
not invent new ones.

## Common Pitfalls

### Pitfall 1: Expanding the public product surface by accident
**What goes wrong:** the implementation adds a new public console script or
documents the installer like a peer to `rdagent-v3-tool`.
**Why it happens:** packaging work often defaults to "add another CLI".
**How to avoid:** keep the installer repo-local and treat it as setup/support
infrastructure, not a new product surface.
**Warning signs:** edits to `[project.scripts]`, new README sections that place
installer commands alongside `rdagent-v3-tool` as a first-class public tool.

### Pitfall 2: Symlink happy-path only
**What goes wrong:** local installs work once on a clean machine, but reruns,
broken links, or existing target directories fail unpredictably.
**Why it happens:** filesystem installers often test only the first install.
**How to avoid:** test create, re-run idempotence, broken-link repair, and
fallback copy mode with `tmp_path`.
**Warning signs:** installer tests only assert "file exists" and never inspect
`is_symlink()` or replacement behavior.

### Pitfall 3: Cleaning README but leaving stale continuity elsewhere
**What goes wrong:** README loses the internal section, but
`.planning/V3-EXTRACTION-HANDOFF.md` still points to `docs/context/*` and
absolute local paths as if they were active.
**Why it happens:** public docs get attention first, archive/history docs get
ignored.
**How to avoid:** treat handoff cleanup and STATE promotion as a single slice
with doc regressions.
**Warning signs:** active docs still mention `docs/context/SESSION-HANDOFF.md`
or `/Users/michael-liang/...` startup steps.

## Code Examples

### Thin CLI wrapper pattern
```python
# Source: v3/entry/tool_cli.py
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rdagent-v3-tool",
        description="Inspect the V3 skill and CLI tool catalog.",
    )
    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")
    subparsers.required = True
    return parser
```

### Direct doc-regression pattern
```python
# Source pattern: tests/test_phase17_surface_convergence.py
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
README = REPO_ROOT / "README.md"

def test_readme_has_no_internal_continuation_section():
    assert "## Continue This Session" not in README.read_text()
```

## Open Questions

1. **Should the stale extraction handoff be rewritten in place or explicitly archived?**
   - What we know: `18-CONTEXT.md` allows historical artifacts to remain, but
     they must stop acting like current truth.
   - Recommendation: keep the file as history, but change its status/wording so
     `.planning/STATE.md` is unambiguously current.

2. **Should local install create missing `./.codex/skills` and `./.claude/skills` directories automatically?**
   - What we know: the user wants local + global targets, and no existing
     installer exists.
   - Recommendation: yes; create missing target directories deterministically
     and document that behavior in README/tests.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | `pytest >=7.4.0` |
| Config file | `pyproject.toml` |
| Quick run command | `uv run python -m pytest tests/test_v3_tool_cli.py tests/test_phase17_surface_convergence.py tests/test_phase18_skill_installation.py tests/test_phase18_planning_continuity.py -q` |
| Full suite command | `uv run python -m pytest tests/test_v3_tool_cli.py tests/test_phase13_v3_tools.py tests/test_phase14_skill_agent.py tests/test_phase16_rd_agent.py tests/test_phase16_tool_surface.py tests/test_phase17_surface_convergence.py tests/test_phase18_skill_installation.py tests/test_phase18_planning_continuity.py -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| STANDALONE-01 | repo env setup stays self-contained, `rdagent-v3-tool` still works, and skill installer links repo-local skills into local/global agent roots without moving CLI tools | unit + smoke | `uv run python -m pytest tests/test_v3_tool_cli.py tests/test_phase18_skill_installation.py -q` | `tests/test_v3_tool_cli.py` ✅ / `tests/test_phase18_skill_installation.py` ❌ Wave 0 |
| STANDALONE-02 | internal continuity lives in `.planning/STATE.md`, README is public-only, and active docs no longer reference stale `docs/context/*` or misleading startup paths | doc-surface regression | `uv run python -m pytest tests/test_phase18_planning_continuity.py -q` | `tests/test_phase18_planning_continuity.py` ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run python -m pytest tests/test_v3_tool_cli.py tests/test_phase17_surface_convergence.py tests/test_phase18_skill_installation.py tests/test_phase18_planning_continuity.py -q`
- **Per wave merge:** `uv run python -m pytest tests/test_v3_tool_cli.py tests/test_phase13_v3_tools.py tests/test_phase14_skill_agent.py tests/test_phase16_rd_agent.py tests/test_phase16_tool_surface.py tests/test_phase17_surface_convergence.py tests/test_phase18_skill_installation.py tests/test_phase18_planning_continuity.py -q`
- **Phase gate:** full suite green plus `uv run lint-imports`

### Wave 0 Gaps
- [ ] `tests/test_phase18_skill_installation.py` — covers symlink install, rerun idempotence, broken-link repair, and copy fallback for STANDALONE-01
- [ ] `tests/test_phase18_planning_continuity.py` — covers README public-only boundary and `.planning/STATE.md` / handoff continuity rules for STANDALONE-02

## Sources

### Primary (HIGH confidence)
- `.planning/phases/18-standalone-packaging-and-planning-autonomy/18-CONTEXT.md` — locked phase decisions and boundaries
- `.planning/PROJECT.md` — milestone goal and constraints
- `.planning/ROADMAP.md` — Phase 18 goal, success criteria, and requirement mapping
- `.planning/REQUIREMENTS.md` — `STANDALONE-01` / `STANDALONE-02` definitions
- `README.md` — current public narrative plus the internal continuation section that must be removed
- `pyproject.toml` — package metadata, test stack, and the single public console script contract
- `.planning/STATE.md` — current internal continuity artifact and starting point for Phase 18 cleanup
- `.planning/V3-EXTRACTION-HANDOFF.md` — stale upstream continuity guidance that must be demoted or rewritten
- `tests/test_v3_tool_cli.py` — existing CLI contract assertions
- `tests/test_phase17_surface_convergence.py` — existing doc-surface regression pattern
- `skills/rd-agent/SKILL.md` and `skills/rd-tool-catalog/SKILL.md` — current canonical repo-local skill source examples
- `uv run python -m pytest tests/test_v3_tool_cli.py tests/test_phase17_surface_convergence.py -q` — current quick regression evidence (`7 passed`)
- `uv run lint-imports` — current boundary-gate evidence (`8 kept, 0 broken`)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - no new dependency is required; current repo stack already covers packaging, CLI, and test needs
- Architecture: HIGH - the packaging boundary, README drift, and continuity seams are explicit in current repo files
- Pitfalls: HIGH - directly derived from current stale docs, public/internal boundary leakage, and filesystem installer risks

**Research date:** 2026-03-21
**Valid until:** 2026-04-20
