from __future__ import annotations

from rd_agent.ports.holdout_port import (
    EvaluationPort,
    FoldSpec,
    HoldoutSplitPort,
    StratifiedKFoldSplitter,
    StubEvaluationPort,
    StubHoldoutSplitPort,
)


def test_fold_spec_constructs() -> None:
    fold = FoldSpec(fold_index=0, train_ref="train-0", holdout_ref="holdout-0")

    assert fold.fold_index == 0
    assert fold.train_ref == "train-0"
    assert fold.holdout_ref == "holdout-0"


def test_stub_holdout_split_port_returns_five_non_empty_folds() -> None:
    splitter = StubHoldoutSplitPort(k=5)

    folds = splitter.split(run_id="run-phase28")

    assert len(folds) == 5
    assert all(isinstance(fold, FoldSpec) for fold in folds)
    assert [fold.fold_index for fold in folds] == [0, 1, 2, 3, 4]
    assert all(fold.train_ref for fold in folds)
    assert all(fold.holdout_ref for fold in folds)


def test_stratified_kfold_splitter_returns_five_non_empty_folds() -> None:
    splitter = StratifiedKFoldSplitter(k=5)

    folds = splitter.split(run_id="run-phase28")

    assert len(folds) == 5
    assert [fold.fold_index for fold in folds] == [0, 1, 2, 3, 4]
    assert all("run-phase28" in fold.train_ref for fold in folds)
    assert all("run-phase28" in fold.holdout_ref for fold in folds)


def test_stub_evaluation_port_returns_mapped_score_and_default() -> None:
    fold = FoldSpec(fold_index=0, train_ref="train-0", holdout_ref="holdout-0")
    evaluator = StubEvaluationPort(scores={"node-1": 0.9})

    assert evaluator.evaluate(candidate_node_id="node-1", fold=fold) == 0.9
    assert evaluator.evaluate(candidate_node_id="missing-node", fold=fold) == 0.5


def test_protocol_shaped_objects_expose_expected_methods() -> None:
    split_port: HoldoutSplitPort = StubHoldoutSplitPort(k=5)
    evaluation_port: EvaluationPort = StubEvaluationPort()

    folds = split_port.split(run_id="run-phase28")
    score = evaluation_port.evaluate(candidate_node_id="node-1", fold=folds[0])

    assert len(folds) == 5
    assert score == 0.5
