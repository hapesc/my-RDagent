# Milestone v1.3 Research — PITFALLS

**Scope:** bad experiences surfaced by real usage logs and reference comparison
**Confidence:** HIGH

## Pitfall 1: Wrong-layer interaction at entry

**Observed:** user wants to solve a task, but the system first teaches them
about run/stage/state contracts.

**Why it happens:** `rd-agent` is both orchestration entrypoint and the place
where intent translation is expected to happen.

**Prevent:** add an intent-first routing layer that decides:
- new run
- continue paused run
- inspect only
- route to stage skill

## Pitfall 2: Paused work is not the default routing anchor

**Observed:** system had to discover after the fact that the correct next
action was `rd-code`, not another `rd-agent` start.

**Why it happens:** paused-run detection exists as agent reasoning, not as a
strong product rule.

**Prevent:** when paused state exists, default to continuation routing first.

## Pitfall 3: Surface text outruns persisted state

**Observed:** a stage could claim the next stage was prepared while the actual
snapshot file was missing.

**Why it happens:** state mutation and operator wording are not bound tightly
enough.

**Prevent:** require snapshot/materialization invariants before success text.

## Pitfall 4: Environment blockers discovered too late

**Observed:** runtime version and dependency failures were discovered only after
real execution work had started.

**Why it happens:** stage entry is not guarded by a strong preflight pass.

**Prevent:** move environment/runtime/data checks ahead of stage execution.

## Pitfall 5: Users ask “what skill next?” too often

**Observed:** after real work, the user still needed to ask which skill should
come next.

**Why it happens:** the system does not expose a sufficiently strong “next
step” surface tied to real state.

**Prevent:** add state-derived next-step recommendations as a first-class
output.

## Pitfall 6: Too much orchestration narration

**Observed:** many intermediate explanations were locally correct but created
UX noise.

**Why it happens:** transparency is treated as the same thing as helpfulness.

**Prevent:** compress default replies to:
- current state
- reason
- next action

## Pitfall 7: Parallel execution can create fake failures

**Observed:** data preparation and training were run in parallel despite a hard
dependency, producing misleading errors.

**Why it happens:** execution scheduling does not enforce dependency shape
strongly enough.

**Prevent:** add explicit DAG-style dependency recognition for stage subwork.
