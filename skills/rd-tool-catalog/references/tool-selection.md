# Tool Selection Guide

Use this reference only after deciding the task should not stay in `rd-agent` or
one of the stage skills.

The source of truth for actual tool metadata remains:

- `v3.entry.tool_catalog`
- `rdagent-v3-tool list`
- `rdagent-v3-tool describe <tool>`

This file is only a routing aid.

## Decision Order

1. Decide whether the task should stay in a high-level skill.
2. If not, choose the top-level `category`.
3. If `category=primitives`, narrow to a `subcategory`.
4. Only then select one direct tool.

## Top-Level Categories

### `orchestration`

Use when the caller needs a high-level round or loop operation rather than a
single read/write primitive.

Representative tools:

- `rd_run_start`
- `rd_explore_round`
- `rd_converge_round`

Typical requests:

- "start the run"
- "run an exploration round"
- "run convergence"

If the caller really wants the default end-to-end path, route back to
`rd-agent` instead of staying in direct tools.

### `inspection`

Use when the caller wants to read existing V3 state without mutating the flow.

Representative tools:

- `rd_run_get`
- `rd_branch_board_get`
- `rd_branch_get`
- `rd_branch_list`
- `rd_stage_get`
- `rd_artifact_list`
- `rd_recovery_assess`
- `rd_memory_get`
- `rd_memory_list`
- `rd_branch_paths_get`

Typical requests:

- "inspect the current run"
- "show branch state"
- "list artifacts"
- "check recovery"

### `primitives`

Use when the caller needs one concrete action instead of a high-level skill or
orchestration round.

Always narrow to a primitive subcategory before choosing the tool.

## Primitive Subcategories

### `branch_lifecycle`

Use for creating, pruning, merging, or falling back between branches.

Representative tools:

- `rd_branch_fork`
- `rd_branch_prune`
- `rd_branch_merge`
- `rd_branch_fallback`

Typical requests:

- "fork a branch"
- "prune low-quality branches"
- "merge shortlisted branches"
- "fall back to the top branch"

### `branch_knowledge`

Use for assessing or applying knowledge sharing across branches.

Representative tools:

- `rd_branch_share_assess`
- `rd_branch_share_apply`

Typical requests:

- "should these branches share knowledge"
- "apply the share decision"

### `branch_selection`

Use for candidate ranking, shortlist creation, or recommending what branch to
advance next.

Representative tools:

- `rd_branch_shortlist`
- `rd_branch_select_next`

Typical requests:

- "build a shortlist"
- "recommend the next branch"

### `memory`

Use for explicit branch-memory creation or promotion.

Representative tools:

- `rd_memory_create`
- `rd_memory_promote`

Typical requests:

- "create a memory"
- "promote this memory to shared"

## Route Back Out

Do not force a direct tool choice when:

- the caller really wants `rd-agent`
- the caller is clearly inside one owned stage and should use `rd-propose`,
  `rd-code`, `rd-execute`, or `rd-evaluate`
- the request is still ambiguous after one category-level narrowing question

In those cases, route back to the higher-level skill instead of guessing.
