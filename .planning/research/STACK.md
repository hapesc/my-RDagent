# Milestone v1.3 Research — STACK

**Scope:** pipeline experience hardening for rdagent
**Reference repo:** `https://github.com/glittercowboy/get-shit-done`
**Confidence:** HIGH

## Current rdagent stack constraints

- Runtime: Python 3.11+, `pydantic`, `pytest`, `import-linter`
- Public surfaces:
  - `skills/rd-agent/SKILL.md`
  - `skills/rd-propose/SKILL.md`
  - `skills/rd-code/SKILL.md`
  - `skills/rd-execute/SKILL.md`
  - `skills/rd-evaluate/SKILL.md`
  - `skills/rd-tool-catalog/SKILL.md`
  - `README.md`
  - `rdagent-v3-tool describe ...`
- State/artifact truth:
  - `.rdagent-v3/` in external usage repos
  - `.planning/STATE.md`, `.planning/PROJECT.md`, `.planning/ROADMAP.md` in the standalone repo

## Reference stack patterns from get-shit-done

- One obvious operator path:
  `new-project/new-milestone -> requirements -> roadmap -> plan-phase -> execute-phase -> verify-work -> complete-milestone`
- Explicit lifecycle commands:
  users are not expected to infer the next step from state internals
- Strong “what’s next” surfaces:
  README, `$gsd-progress`, and milestone/phase commands always orient the user
- Brownfield/new-project split:
  the system distinguishes “starting new work” from “continuing existing work”
- State artifacts exist, but user guidance sits above them:
  `PROJECT.md`, `STATE.md`, `ROADMAP.md`, `REQUIREMENTS.md` support the pipeline
  without becoming the primary UX burden

## Implications for rdagent

- The main product gap is not core orchestration power; it is the lack of a
  higher layer that translates user intent into the correct skill and next step.
- The next milestone should optimize:
  - intent routing
  - preflight checks
  - state truth and next-step guidance
  rather than adding more low-level primitives first.

## Recommended stack additions

- No new runtime dependency is required to start this milestone.
- Prefer doc/control-plane changes first:
  - entry routing layer
  - state inspection helpers
  - concise next-step reporting
- If an environment repair flow is added, keep it repo-local and contract-first
  instead of creating a hidden magic fallback.
