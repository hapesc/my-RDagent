from __future__ import annotations

import random

from data_models import DataSplitManifest


class StratifiedSplitter:
    def __init__(
        self,
        train_ratio: float = 0.9,
        test_ratio: float = 0.1,
        seed: int = 42,
    ) -> None:
        self._train_ratio = train_ratio
        self._test_ratio = test_ratio
        self._seed = seed

    def split(
        self,
        data_ids: list[str],
        labels: list[str] | None = None,
    ) -> DataSplitManifest:
        if not data_ids:
            return DataSplitManifest(train_ids=[], val_ids=[], test_ids=[], seed=self._seed)

        rng = random.Random(self._seed)

        if labels is not None and len(labels) == len(data_ids):
            return self._stratified_split(data_ids, labels, rng)
        return self._random_split(data_ids, rng)

    def _random_split(self, data_ids: list[str], rng: random.Random) -> DataSplitManifest:
        ids = list(data_ids)
        rng.shuffle(ids)
        n = len(ids)
        n_test = max(1, round(n * self._test_ratio)) if n > 1 else 0
        n_train = n - n_test
        return DataSplitManifest(
            train_ids=ids[:n_train],
            val_ids=[],
            test_ids=ids[n_train:],
            seed=self._seed,
        )

    def _stratified_split(
        self,
        data_ids: list[str],
        labels: list[str],
        rng: random.Random,
    ) -> DataSplitManifest:
        groups: dict[str, list[str]] = {}
        for data_id, label in zip(data_ids, labels, strict=False):
            groups.setdefault(label, []).append(data_id)

        train_ids: list[str] = []
        test_ids: list[str] = []

        for label in sorted(groups):
            group = groups[label]
            rng.shuffle(group)
            n = len(group)
            n_test = max(1, round(n * self._test_ratio)) if n > 1 else 0
            n_train = n - n_test
            train_ids.extend(group[:n_train])
            test_ids.extend(group[n_train:])

        return DataSplitManifest(
            train_ids=train_ids,
            val_ids=[],
            test_ids=test_ids,
            seed=self._seed,
        )
