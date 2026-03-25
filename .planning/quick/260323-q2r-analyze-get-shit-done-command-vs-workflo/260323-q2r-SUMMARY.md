# Quick Task 260323-q2r Summary

**Description:** Analyze get-shit-done command-vs-workflow split for stricter RDagent pipeline enforcement
**Date:** 2026-03-23
**Status:** Summary drafted; STATE/commit intentionally deferred pending user approval

## What GSD is actually doing

The split is not “UI file vs another doc file.” It is a control-boundary split.

### 1. Commands are thin public entry surfaces

Representative files like `commands/gsd/quick.md` are deliberately thin:

- frontmatter for name, description, argument shape, and allowed tools
- a short objective
- `execution_context` that points to the real workflow
- `process` text that explicitly says “execute the workflow end-to-end”

That means the user-facing surface is stable and simple, but the command file is
not where the real state machine lives.

### 2. Workflows are the canonical pipeline definitions

Files like `get-shit-done/workflows/quick.md` hold the actual ordered process:

- argument parsing
- init/tool calls
- gating and mode branches
- artifact paths
- state update rules
- commit behavior
- success criteria

This is the operative pipeline contract, not a suggestion layer.

### 3. `gsd-tools.cjs` is the deterministic enforcement rail

GSD does not let every command/workflow invent its own ad hoc shell logic for:

- loading state
- resolving context
- generating ids/slugs
- validating health
- mutating planning state
- committing planning artifacts

Those all collapse into `get-shit-done/bin/gsd-tools.cjs`, so workflows are
thin orchestrators over a shared deterministic tool layer.

### 4. Internal workflows exist and are intentionally not user-addressable

`get-shit-done/workflows/transition.md` explicitly declares itself an internal
workflow and says there is no `/gsd:transition` command. That matters because it
shows GSD is not treating every orchestration step as a public surface. Some
pipeline steps are reserved for the orchestrator only.

## What this implies for RDagent

If we want stricter pipeline compliance, the main lesson is not just “split a
file into two files.” The lesson is to split responsibilities so the agent
cannot easily drift.

### 1. Public skill should not be the canonical workflow

Our current RDagent skills still carry too much operative contract directly in
`SKILL.md`. That helps discoverability, but it also means the same file is doing
both:

- activation/public UX
- orchestration policy
- low-level tool routing guidance

That makes it easier for the agent to partially obey the surface while skipping
the intended pipeline.

### 2. Workflow files should be the single authoritative pipeline

We should introduce a dedicated internal workflow layer for RDagent:

- public command/skill wrapper
- internal workflow spec
- deterministic CLI/tool layer

The public skill should mostly do:

1. validate entry conditions
2. load the workflow
3. execute that workflow
4. refuse to improvise outside it

### 3. Internal-only workflows are a missing primitive for us

We need the equivalent of GSD’s internal `transition` workflow for steps that
should never be user-invoked directly but that must still be performed
consistently by the orchestrator.

For RDagent, examples are likely:

- paused-run continuation repair routing
- preflight-before-stage handoff
- fresh-start vs resume arbitration
- branch-selection / convergence transitions

If these stay only as narrative text in public skills, the agent can bypass
them. If they become internal workflows, the orchestrator can own them.

### 4. Tool layer should become more opinionated and less descriptive

Right now we improved the install surface and tool invocation root, but our tool
layer is still more descriptive than enforcing compared with GSD. The stronger
pattern is:

- workflows ask tools for authoritative state/context
- workflows use tools to mutate canonical state
- workflows use tools to commit or verify artifacts
- skills do not freehand state reconstruction when a tool should decide

## Concrete recommendations for RDagent

### Recommendation A: Split `skill` from `workflow`

Create an internal directory such as:

- `workflows/rd-agent-start.md`
- `workflows/rd-agent-continue.md`
- `workflows/rd-stage-continue.md`
- `workflows/rd-tool-downshift.md`
- `workflows/rd-transition.md` (internal only)

Then keep public `skills/*/SKILL.md` thin:

- trigger surface
- required public arguments
- one sentence on when to use
- `execution_context` pointing to the workflow
- explicit “follow the workflow; do not improvise”

### Recommendation B: Add internal-only workflow boundaries

Do not expose every pipeline step as a public skill. Some steps should be
orchestrator-only, especially where correctness depends on ordered gates.

### Recommendation C: Move more control into deterministic tools

The more pipeline-critical logic that stays in prose, the easier it is for the
agent to “mostly comply.” Push these into tools:

- current-state resolution
- allowed next-step resolution
- preflight/blocker truth
- quick/state artifact bookkeeping
- install/runtime-root discovery

### Recommendation D: Treat public skills as adapters, not executors

This is the biggest mindset shift. Public skills should be adapters that load a
workflow and expose a stable UX. They should not themselves be the full
pipeline.

## One step beyond the obvious

The deepest takeaway is not “command vs workflow.” It is “public surface vs
authoritative control plane.”

If we only copy the file split but keep the real authority in public skill
prose, nothing meaningful changes. The hard requirement is:

- the user-facing layer may describe
- the workflow layer may orchestrate
- the tool layer must decide

Without that third layer, the split stays cosmetic.
