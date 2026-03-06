# Task-19 Synthetic Research

## Goal

Promote the previous minimal/example plugin into the formal second product scenario `synthetic_research`.

## Public scenario entry

`build_default_registry()` now publicly exposes:

- `data_science`
- `synthetic_research`

The legacy example builder `build_minimal_data_science_bundle()` remains only as a compatibility wrapper for older tests/helpers and is no longer registered as a public scenario.

## Scenario behavior

`synthetic_research` runs on the same loop engine and plugin contracts as `data_science`:

- proposal
- experiment generation
- coding
- running
- feedback
- record/checkpoint

The scenario writes:

- `research_brief.md`
- `research_notes.txt`
- `research_summary.json`

under the loop workspace, so artifact listing and trace queries work without adding engine-level scenario branches.

## Shared manifest

The scenario is registered with a formal `ScenarioManifest`:

- `scenario_name`: `synthetic_research`
- `title`: `Synthetic Research`
- `supports_branching`: `true`
- `supports_resume`: `true`

CLI exposure is available through:

```bash
python3 agentrd_cli.py health-check --verbose
```

## Minimal run example

```bash
python3 agentrd_cli.py run \
  --scenario synthetic_research \
  --loops-per-call 1 \
  --input '{"task_summary":"summarize LLM eval directions","reference_topics":["alignment","benchmarking"],"max_loops":1}'
```
