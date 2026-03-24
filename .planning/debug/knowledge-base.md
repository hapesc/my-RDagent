# GSD Debug Knowledge Base

Resolved debug sessions. Used by `gsd-debugger` to surface known-pattern hypotheses at the start of new investigations.

---

## phase28-multi-branch-service-quality — Code quality issues in multi_branch_service.py (oversized function, broad except, dynamic import, hasattr duck-typing)
- **Date:** 2026-03-24
- **Error patterns:** run_exploration_round 212 lines, except Exception, __import__ dynamic import, hasattr duck-typing, merge_with_complementarity
- **Root cause:** Four independent code quality issues accumulated during Phase 28 development: oversized function, overly broad exception handler, unnecessary dynamic import, redundant hasattr check
- **Fix:** Decomposed into 10 helper methods, narrowed except to (KeyError, ValueError), replaced __import__ with static import, removed hasattr guard
- **Files changed:** v3/orchestration/multi_branch_service.py
---

