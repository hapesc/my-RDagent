# Agentic R&D Platform PRD

> Status: reverse-engineered product requirements  
> Audience: coding agents, engineers, technical PMs  
> Goal: define an implementation-ready product scope for a system with functionality similar to `RD-Agent`

## 1. Document Purpose

This PRD describes a product that automates iterative R&D workflows using LLMs, code execution sandboxes, trace persistence, and scenario plugins.

It is intentionally written to be executable by a coding agent:

- requirements are explicit
- scope is staged
- interfaces and acceptance criteria are concrete
- non-goals are called out to prevent scope drift

## 2. Product Summary

### 2.1 Product Name

Working name: `Agentic R&D Platform`

### 2.2 One-Sentence Description

A platform that continuously proposes experiments, writes code, runs it in a sandbox, evaluates outcomes, and iterates while preserving a full, branchable trace of the process.

### 2.3 Product Thesis

Most "AI coding agents" stop at code generation. A useful R&D system must also:

- structure the problem by scenario
- run generated code safely
- compare outcomes across iterations
- persist and replay decisions
- support recovery, branching, and operator control

## 3. Problem Statement

Researchers and engineers currently stitch together:

- prompt sessions
- ad hoc scripts
- notebook experiments
- local logs
- manual reruns

This causes four failures:

- good intermediate ideas are lost
- failed runs are not systematically learned from
- code generation is not tied to actual execution outcomes
- long-running workflows cannot be paused, resumed, or audited cleanly

## 4. Target Users

### 4.1 Primary Users

- ML engineers running iterative experiments
- quant researchers exploring factor/model ideas
- applied AI engineers automating scenario-specific code generation loops

### 4.2 Secondary Users

- engineering managers reviewing agent productivity
- platform teams building domain-specific plugins
- evaluators inspecting full experiment histories

## 5. Jobs To Be Done

- "When I have a scenario and dataset, I want the system to iteratively improve a solution so I do not have to manually rerun every idea."
- "When a run fails halfway, I want to resume from the last stable step instead of restarting."
- "When the agent tries multiple directions, I want to inspect branches and keep the best path."
- "When I introduce a new domain, I want to add a plugin bundle instead of rewriting the engine."
- "When I review results, I want to see hypothesis, code changes, outputs, and feedback in one place."

## 6. Product Goals

### 6.1 Business / Product Goals

- reduce manual experiment orchestration work
- increase repeatability and auditability of agentic development
- provide a reusable base for multiple R&D scenarios

### 6.2 User Goals

- start a run with minimal manual glue code
- monitor and control long-running loops
- retain full historical context
- reuse successful patterns across runs

### 6.3 Success Metrics

- `M1` A new run can be started from CLI or API in under 2 minutes after environment setup.
- `M2` A paused or crashed run can resume from latest checkpoint with no more than one step of lost work.
- `M3` A complete trace is viewable for 100% of successful runs.
- `M4` At least one scenario plugin can complete a full proposal -> code -> run -> feedback loop end-to-end.
- `M5` Plugin authors can add a second scenario without modifying loop-engine core modules.

## 7. Product Scope

### 7.1 MVP

The MVP must include:

- one end-to-end scenario plugin
- local CLI
- local persistence
- loop engine
- sandboxed execution backend
- checkpoint resume
- trace event storage
- basic web trace viewer

### 7.2 V1

V1 adds:

- multiple scenario plugins
- REST control plane
- branch-aware trace view
- per-step model and timeout config
- operator pause/resume/stop controls

### 7.3 Later

- multi-worker scheduling
- knowledge base retrieval and accumulation
- branch merge strategies
- approval workflows
- artifact comparison dashboards

## 8. User Flows

### 8.1 Create And Run

1. user selects scenario and input payload
2. system validates environment and input
3. system creates run session
4. system enters iterative loop
5. UI and API stream trace events

### 8.2 Pause And Resume

1. user pauses run
2. system finishes or safely interrupts current step
3. latest checkpoint remains available
4. user resumes later
5. system restarts from latest checkpoint

### 8.3 Resume From History / Fork

1. user selects historical checkpoint
2. system either truncates future state or forks a new branch
3. new branch continues independently

### 8.4 Review Outcome

1. user opens run trace
2. user inspects hypothesis, code changes, runtime outputs, feedback, and metrics
3. user exports or promotes the final artifact

## 9. Functional Requirements

Each requirement is written so a coding agent can implement and test it directly.

### FR-001 Scenario Registration

The system shall support registration of scenario plugin bundles.

Acceptance criteria:

- new scenario can be added by configuration and plugin class references
- core loop engine requires no scenario-specific conditionals for normal operation
- each scenario exposes context-building, proposal, experiment generation, coding, running, and feedback contracts

### FR-002 Run Creation

The system shall create a new run from CLI or API input.

Acceptance criteria:

- run receives a unique `run_id`
- run metadata includes scenario name, input payload, stop conditions, and creation time
- invalid scenario or invalid payload yields structured error response

### FR-003 Iterative Loop Execution

The system shall execute the canonical loop:

`propose -> experiment_generation -> coding -> running -> feedback -> record`

Acceptance criteria:

- step transitions are recorded
- stop conditions on loops, steps, or duration are enforced
- step failures are surfaced and recorded

### FR-004 Workspace Management

The system shall manage a per-experiment workspace containing source files and outputs.

Acceptance criteria:

- workspace can be created, copied, and checkpointed
- files can be injected programmatically
- workspace artifacts are persisted for later inspection

### FR-005 Multi-Round Code Evolution

The system shall support iterative code refinement before final execution.

Acceptance criteria:

- coding stage can run multiple internal rounds
- each round emits code-related events
- system can choose best acceptable intermediate version instead of always last version

### FR-006 Sandboxed Execution

The system shall execute generated code in a controlled backend.

Acceptance criteria:

- backend must support at least one of docker / conda / local sandbox for MVP
- runtime timeout is enforced
- stdout, exit code, runtime, and output files are captured

### FR-007 Feedback And Promotion

The system shall analyze execution results and decide whether the current experiment should be accepted.

Acceptance criteria:

- feedback includes `decision`, `acceptable`, and `reason`
- current experiment can be compared with branch baseline or global best-so-far
- accepted experiments become candidates for subsequent iterations

### FR-008 Trace Persistence

The system shall persist structured trace events for every run.

Acceptance criteria:

- each loop records hypothesis, coding events, execution result, and feedback
- trace is queryable by run ID
- trace remains available after process restart

### FR-009 Checkpoint Resume

The system shall checkpoint state after each successful step.

Acceptance criteria:

- latest checkpoint can restore loop state
- resume restarts from next unfinished step
- crash after checkpoint does not require rerunning previous successful steps

### FR-010 Branching

The system shall support branching from historical checkpoints or prior accepted nodes.

Acceptance criteria:

- branch stores parent reference
- multiple branches can coexist within a run
- trace viewer can distinguish branches

### FR-011 Pause / Resume / Stop Control

The system shall allow operators to control a live run.

Acceptance criteria:

- pause request transitions run to `PAUSED`
- resume returns run to active execution
- stop halts further loop scheduling
- final status is visible through API and UI

### FR-012 Human Instructions

The system shall allow operator instructions to be attached to future experiments.

Acceptance criteria:

- instructions are stored in run or branch context
- downstream proposal or coding stages can access them
- instructions are visible in trace output

### FR-013 Artifact Access

The system shall store and expose artifacts generated during a run.

Acceptance criteria:

- user can list artifacts by run and node
- artifacts include workspace files and execution outputs
- final result can be downloaded or inspected

### FR-014 Observability UI

The system shall provide a basic web UI for trace inspection.

Acceptance criteria:

- user can open a run timeline
- user can inspect hypothesis, code, runtime output, feedback, and metrics
- UI can refresh incrementally as new events arrive

### FR-015 REST Control API

The system shall expose a service interface for run control and trace retrieval.

Acceptance criteria:

- API supports create, get status, pause, resume, stop, events, and artifacts
- all API responses use structured JSON
- error responses include stable error codes or error types

### FR-016 Knowledge Base

The system should support optional storage and retrieval of reusable knowledge.

Acceptance criteria:

- feature can be disabled without affecting core loop behavior
- successful ideas and selected failures can be stored
- proposal and coding stages can query retrieved knowledge when enabled

### FR-017 Configurability

The system shall support environment-variable and file-based configuration.

Acceptance criteria:

- execution limits, model routing, backend choice, and storage paths are configurable
- scenario-level config can override defaults
- config values are inspectable for a run

### FR-018 Health Check

The system shall provide a health check command or endpoint.

Acceptance criteria:

- verifies control-plane readiness
- verifies execution backend availability
- verifies configured LLM connectivity when enabled

## 10. Non-Functional Requirements

### NFR-001 Reliability

- checkpoint after each successful step
- append-only or durable trace persistence
- no silent loss of accepted experiment state

### NFR-002 Reproducibility

- run config snapshot must be stored with each run
- artifact paths must be stable and attributable
- feedback decisions must be auditable

### NFR-003 Performance

- control-plane actions should return within 2 seconds for local metadata operations
- UI trace page should load first page of events within 5 seconds for normal run sizes

### NFR-004 Isolation

- generated code must not execute inside the control-plane process without explicit local-backend opt-in
- execution timeouts must be enforced

### NFR-005 Extensibility

- adding a new scenario plugin must not require edits in more than one or two registration files

### NFR-006 Observability

- every step transition must be logged
- every exception must be stored with run and step context

### NFR-007 Operator Safety

- secrets must not be emitted into trace payloads
- workspace content must be treated as untrusted

## 11. Product Constraints

- primary implementation target is Linux
- Python 3.11 recommended
- sandbox backend requires host support for chosen runtime, usually Docker
- LLM provider must support structured or reliably parseable outputs for core stages

## 12. Out Of Scope

- arbitrary browser automation
- collaborative multi-user editing
- hosted billing / tenancy model
- full notebook IDE
- enterprise RBAC

## 13. Release Plan

### P0: Engine Foundation

Deliver:

- schemas
- plugin interfaces
- run metadata store
- local filesystem artifact store
- local loop execution
- one execution backend

Exit criteria:

- one synthetic scenario completes a full loop

### P1: Usable Local Product

Deliver:

- one real scenario plugin
- checkpoint resume
- trace store
- CLI
- minimal web UI

Exit criteria:

- operator can run, pause, resume, and inspect a local run end-to-end

### P2: Service Product

Deliver:

- REST API
- branch support
- artifact listing
- run control endpoints

Exit criteria:

- a remote client can create and monitor runs without direct process access

### P3: Advanced Agentic Features

Deliver:

- knowledge base
- branch comparison
- multi-scenario support
- per-step model routing

Exit criteria:

- two distinct scenario plugins can run on the same engine

## 14. Acceptance Test Matrix

### A1 End-to-End Run

- create run
- complete at least one full loop
- persist hypothesis, code event, execution result, and feedback

### A2 Resume

- interrupt run after coding or running step
- restart service
- resume from latest checkpoint

### A3 Branch

- fork from previous accepted node
- continue new branch
- verify both branches visible in trace

### A4 Sandbox

- run code that exceeds timeout
- confirm execution backend terminates it
- confirm failure is recorded

### A5 Plugin Swap

- register second minimal scenario
- run without changing loop-engine implementation

## 15. Risks

- poorly defined plugin contracts will force core-engine changes later
- direct execution on host can create safety and reproducibility problems
- trace persistence can become inconsistent if feedback and record are concurrent
- over-investing in prompts before building durable state will create a fragile demo

## 16. Open Decisions

These choices should be made early by the implementation team:

- whether historical resume truncates future state or always forks
- whether UI is Streamlit-first or custom frontend
- whether event store is SQLite-only for MVP or abstracted immediately
- whether LLM adapter targets LiteLLM compatibility from day one

## 17. Definition Of Done

This product is implementation-complete for `v1` when:

- one operator can start a real run from CLI or API
- the system writes code, runs it, scores it, and records feedback
- the run can be resumed after interruption
- trace and artifacts are inspectable in UI
- a second scenario can be added via plugin contract

## 18. Coding-Agent Handoff Instructions

If this PRD is handed to a coding agent, the agent should implement in this order:

1. data models and plugin protocols
2. run/session persistence
3. workspace manager and execution backend
4. loop engine
5. first scenario plugin
6. checkpoint resume
7. trace store and UI
8. REST control layer

The agent should avoid starting with:

- prompt optimization
- visual polish
- advanced retrieval
- multi-worker scale

Those are multipliers, not foundations.
