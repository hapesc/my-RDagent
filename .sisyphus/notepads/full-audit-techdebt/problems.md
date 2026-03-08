## Problems

- Plan-name drift already occurred once between `paper-fc23-upgrade` and `paper-fc2-fc3`; avoid recreating stale boulder state.
- The repository is already dirty from plan/session metadata changes, so verification must distinguish our changes from historical noise.
- Import-cycle fixes and capability cleanup can easily sprawl into architecture refactors if scope is not tightly enforced.
- Doc fixes can balloon if treated as prose cleanup; only stale technical contradictions belong in scope.
