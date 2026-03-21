# Phase 17 External Reference Notes

**Captured:** 2026-03-21
**Purpose:** Preserve external design inspirations discussed during Phase 17 context gathering in a repo-local artifact that downstream agents can read directly.

## Sources

### Skill set and workflow packaging references

- `https://github.com/gsd-build/get-shit-done`
  - Takeaway: expose a clear workflow-first surface with a small set of named entrypoints rather than treating every primitive as a first-class starting point.
  - Relevance to Phase 17: supports making `rd-agent` the default orchestration skill and treating the rest of the surface as guided entrypoints.

- `https://github.com/obra/superpowers/tree/main`
  - Takeaway: skills should be flat, discoverable, and single-purpose; a thin guidance skill can route agents toward the right specialized skill.
  - Relevance to Phase 17: supports creating real `skills/.../SKILL.md` packages and considering a thin routing skill if `skill-architect` judges it useful.

### Tool-use design reference

- `https://www.anthropic.com/engineering/advanced-tool-use`
  - Takeaway: tool discovery should be on-demand, higher-level orchestration should hide unnecessary primitive complexity, and usage guidance matters as much as JSON schemas.
  - Relevance to Phase 17: supports making `rd-tool-catalog` a decision-oriented skill, classifying tools explicitly, and preferring high-level skills before dropping to primitives.

## Applied Decisions

- Phase 17 will create real agent-facing skill packages instead of only renaming terminology.
- Skill creation and refactoring must go through `$skill-architect`.
- `rd-agent` remains the primary orchestration entrypoint.
- CLI tools need explicit categories and stable structured metadata so skills and tests can consume them directly.

