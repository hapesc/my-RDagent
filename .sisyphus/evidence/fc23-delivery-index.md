# FC-2 / FC-3 Delivery Index

Current branch: `feat/paper-fc-implementation`

Latest implementation and verification commits:

- `340d23b` `feat(fc2): rewrite MCTSScheduler with paper-faithful PUCT + backpropagation + RewardCalculator`
- `57bed5f` `feat(fc3): add ReasoningPipeline trace persistence via trace_store injection`
- `b7d0635` `feat(fc3): CoSTEER structured 3-dim feedback + knowledge self-generation`
- `7385226` `feat(fc2): add tree structure, observe_feedback, and generate_diverse_roots to ExplorationManager`
- `97ddc93` `feat(fc2): upgrade LoopEngine MCTS flow — observe_feedback replaces update_visit_count`
- `0f3ef76` `feat(config): add MCTS config fields and wire RewardCalculator + VirtualEvaluator in runtime`
- `cf624a0` `test(fc2-fc3): add E2E coverage and update gap analysis to complete implementations`
- `663fbc6` `docs(evidence): add Wave 4 verification artifacts for FC-2 and FC-3 upgrade`
- `887f603` `docs(evidence): refresh final QA report with Wave 4 regression addendum`
- `fd37325` `docs(evidence): add final test accounting for Wave 4 regression`
- `32cfb24` `fix(fc2-fc3): wire CoSTEER runtime dependencies and close final audit gaps`

Primary implementation files:

- `exploration_manager/scheduler.py`
- `exploration_manager/service.py`
- `core/loop/engine.py`
- `core/loop/step_executor.py`
- `core/loop/costeer.py`
- `core/reasoning/pipeline.py`
- `app/config.py`
- `app/runtime.py`

Primary verification files:

- `tests/test_scheduler_mcts.py`
- `tests/test_exploration_manager.py`
- `tests/test_loop_engine_mcts.py`
- `tests/test_runtime_wiring.py`
- `tests/test_e2e_fc2_fc3.py`
- `tests/test_e2e_fc3.py`

Key evidence files:

- `task-13-e2e-mcts.txt`
- `task-13-e2e-compat.txt`
- `task-14-e2e-feedback.txt`
- `task-14-e2e-full-loop.txt`
- `task-15-regression.txt`
- `task-15-test-accounting.txt`
- `task-15-gap-doc.txt`
- `task-15-contracts-unchanged.txt`
- `task-16-final-fixes.txt`
- `final-qa/FINAL-QA-REPORT.md`

Current regression baseline:

- `547 passed, 3 warnings`

Warnings status:

- 3 `PytestCollectionWarning` entries from `app/fastapi_compat.py:125`
- They are pre-existing and unrelated to the FC-2 / FC-3 upgrade path

Contracts status:

- `plugins/contracts.py` unchanged during FC-2 / FC-3 upgrade
