# Quick Task 260323-qfz: Extract actionable skill-improvement guidance from Google skill patterns for RDagent

**Date:** 2026-03-23
**Status:** Completed
**Description:** Extract actionable skill-improvement guidance from Google skill patterns for RDagent

## Scope

Translate the five published skill patterns into concrete improvements for
RDagent skill design, with emphasis on stricter pipeline compliance rather than
generic prompt-writing advice.

## Tasks

### Task 1

**Files:** User-provided Google pattern summary, `get-shit-done` command and
workflow examples

**Action:** Map the five named patterns to the existing RDagent skill surface
and identify which problems each pattern actually solves for us.

**Verify:** The analysis should distinguish public-surface concerns from
orchestration/control-plane concerns.

**Done:** Pattern-to-RDagent mapping established.

### Task 2

**Files:** `.planning/quick/260323-qfz-extract-actionable-skill-improvement-gui/260323-qfz-SUMMARY.md`

**Action:** Write concrete recommendations that go beyond the article’s generic
examples, especially where RDagent needs public-skill thinning, internal
workflow ownership, stronger tool authority, and better negative routing.

**Verify:** Recommendations should be implementable as repo changes, not just
abstract opinions.

**Done:** Summary drafted with architectural recommendations and migration
sequence.
