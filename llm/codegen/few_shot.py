from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

ArtifactType = Literal["code", "structured_text"]


@dataclass(frozen=True)
class FewShotExample:
    task: str
    artifact: str
    artifact_type: ArtifactType
    explanation: str


_REGISTRY: dict[str, list[FewShotExample]] = {}


def register_examples(scenario: str, examples: list[FewShotExample]) -> None:
    _REGISTRY[scenario] = list(examples)


def get_few_shot_examples(scenario: str) -> list[dict[str, str]]:
    return [asdict(example) for example in _REGISTRY.get(scenario, [])]


register_examples(
    "quant",
    [
        FewShotExample(
            task="Build a 5-day momentum factor from adjusted close prices.",
            artifact="""import pandas as pd


def compute_factor(df: pd.DataFrame) -> pd.DataFrame:
    frame = df.sort_values(["stock_id", "date"]).copy()
    frame["factor_value"] = frame.groupby("stock_id")["close"].pct_change(5).fillna(0.0)
    return frame[["date", "stock_id", "factor_value"]]
""",
            artifact_type="code",
            explanation="Shows the required compute_factor signature and grouped pct_change logic.",
        ),
        FewShotExample(
            task="Build a 20-day rolling volatility factor from daily close-to-close returns.",
            artifact="""import pandas as pd


def compute_factor(df: pd.DataFrame) -> pd.DataFrame:
    frame = df.sort_values(["stock_id", "date"]).copy()
    returns = frame.groupby("stock_id")["close"].pct_change()
    frame["factor_value"] = returns.groupby(frame["stock_id"]).rolling(20).std().reset_index(level=0, drop=True)
    frame["factor_value"] = frame["factor_value"].fillna(0.0)
    return frame[["date", "stock_id", "factor_value"]]
""",
            artifact_type="code",
            explanation="Demonstrates rolling standard deviation with the expected output columns.",
        ),
    ],
)

register_examples(
    "data_science",
    [
        FewShotExample(
            task="Train a classifier and write evaluation metrics to metrics.json.",
            artifact="""import json
from pathlib import Path

from sklearn.datasets import load_iris
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import train_test_split


def main() -> None:
    features, labels = load_iris(return_X_y=True)
    x_train, x_test, y_train, y_test = train_test_split(features, labels, test_size=0.2, random_state=42)
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(x_train, y_train)
    predictions = model.predict(x_test)
    metrics = {
        "accuracy": accuracy_score(y_test, predictions),
        "f1_macro": f1_score(y_test, predictions, average="macro"),
    }
    Path("metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
""",
            artifact_type="code",
            explanation="Includes metrics.json output and concrete classification metrics.",
        ),
        FewShotExample(
            task="Train a regression pipeline and write RMSE metrics to metrics.json.",
            artifact="""import json
from pathlib import Path

import numpy as np
from sklearn.datasets import make_regression
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split


def main() -> None:
    features, targets = make_regression(n_samples=300, n_features=8, noise=12.0, random_state=7)
    x_train, x_test, y_train, y_test = train_test_split(features, targets, test_size=0.2, random_state=7)
    model = GradientBoostingRegressor(random_state=7)
    model.fit(x_train, y_train)
    predictions = model.predict(x_test)
    metrics = {
        "rmse": float(np.sqrt(mean_squared_error(y_test, predictions))),
        "r2": r2_score(y_test, predictions),
    }
    Path("metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
""",
            artifact_type="code",
            explanation="Shows regression metrics and file output expectations.",
        ),
    ],
)

register_examples(
    "synthetic_research",
    [
        FewShotExample(
            task="Write a structured report with quantitative trend findings.",
            artifact="""## Findings

1. Temperature anomalies increased by roughly 0.9 degrees from 1950 to 2020, with the steepest slope after 1980.
2. The post-1995 segment shows faster year-over-year increase than the 1950-1980 baseline.

## Methodology

- Reviewed the anomaly trend as a time series and highlighted inflection periods with visible slope changes.
- Anchored claims with explicit numeric deltas instead of generic descriptions.

## Conclusion

- The dominant pattern is a sustained long-run increase with acceleration in the late 20th century.
""",
            artifact_type="structured_text",
            explanation="Demonstrates headings, numbered findings, and quantitative evidence.",
        ),
        FewShotExample(
            task="Write a comparative report with structured findings across alternatives.",
            artifact="""## Results

1. Adam reached the target loss in 18 steps, faster than RMSProp at 24 and SGD at 41.
2. SGD was the most sensitive to learning-rate changes, with unstable convergence once the rate exceeded 0.1.

## Methodology

- Compared convergence speed, final loss, and sensitivity using the same quadratic objective.
- Reported direct numeric comparisons so each finding is falsifiable.

## Conclusion

- Adam provides the best speed-stability trade-off for this synthetic objective, while SGD needs tighter tuning.
""",
            artifact_type="structured_text",
            explanation="Shows comparative findings with explicit structure and quantitative support.",
        ),
    ],
)
