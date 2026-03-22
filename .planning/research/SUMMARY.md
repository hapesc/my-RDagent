# Milestone v1.3 Research Summary

**Topic:** rdagent pipeline optimization using `gsd-build/get-shit-done` as a
reference and real Kaggle-style `rd-agent` conversations as evidence
**Confidence:** HIGH

## Reference Findings

The reference pipeline is good not because it has more artifacts, but because
it hides orchestration complexity behind a clearer operator path. Its strongest
patterns are:

- one visible lifecycle path
- explicit “what’s next?” guidance
- clear separation between starting new work and continuing existing work
- state artifacts that support the workflow without becoming the main UX burden

## rdagent Weaknesses Exposed by Real Usage

- users still have to think too early about which skill to invoke
- paused runs are not treated as the default routing anchor
- environment/runtime blockers appear too late
- surface claims and persisted state can drift apart
- users must still ask “what skill next?”
- default replies can be too verbose about internal orchestration

## Recommended Milestone Direction

Treat the next milestone as a pipeline experience hardening milestone, not a
new-model or new-tool milestone.

### Focus area 1: Intent-first routing

The user should be able to say what they want, while the system decides whether
to start, continue, inspect, or downshift.

### Focus area 2: Early preflight and blocker surfacing

The system should surface runtime, dependency, data, and state blockers before
stage execution claims readiness.

### Focus area 3: Truthful progress and next-step UX

Operator-facing guidance should come from real persisted state and always answer
the next action without making the user reverse-engineer the pipeline.

## Recommended Requirement Themes

- intent routing and paused-run detection
- environment/data/state preflight checks
- state truth and snapshot consistency
- operator-facing progress and next-step guidance

## Recommended Roadmap Shape

- one phase for intent-first routing
- one phase for preflight and state-truth hardening
- one phase for operator-facing progress / next-step UX

## Sources Used

- `https://github.com/glittercowboy/get-shit-done`
- local GSD workflow docs already vendored in `/Users/michael-liang/.codex/get-shit-done/`
- real user logs from:
  - `/Users/michael-liang/Code/aerial-cactus-identification/.waylog/history/2026-03-21_15-59-59Z-codex-rd-agent-description-to-assess-the-impact-of-clim.md`
  - `/Users/michael-liang/Code/aerial-cactus-identification/.waylog/history/2026-03-22_07-16-18Z-codex-rd-agent.md`
- formalized UX issue report:
  - `.planning/research/RDAGENT-REAL-WORLD-UX-REPORT.md`
