from __future__ import annotations

from scenarios.quant.plugin import evaluate_quant_quality
from scenarios.quant.prompts import FACTOR_CODE_EXAMPLE


def test_valid_factor_code_passes() -> None:
    code = (
        "import pandas as pd\n"
        "def compute_factor(df):\n"
        "    result = df[['date','stock_id']].copy()\n"
        "    result['factor_value'] = df.groupby('stock_id')['close'].pct_change(5)\n"
        "    return result\n"
    )
    assert evaluate_quant_quality(code=code, backtest_metrics={"sharpe": 0.6}).passed is True


def test_template_factor_code_fails() -> None:
    result = evaluate_quant_quality(code=FACTOR_CODE_EXAMPLE, backtest_metrics={})
    assert result.passed is False


def test_factor_without_compute_factor_fails() -> None:
    code = "import pandas as pd\ndef my_alpha(df):\n    pass"
    result = evaluate_quant_quality(code=code, backtest_metrics={"sharpe": 0.6})
    assert result.passed is False
    assert "compute_factor" in result.reasons[0]


def test_factor_with_os_import_fails() -> None:
    code = "import os\nimport pandas as pd\ndef compute_factor(df):\n    pass"
    result = evaluate_quant_quality(code=code, backtest_metrics={})
    assert result.passed is False


def test_empty_backtest_payload_fails() -> None:
    code = "import pandas as pd\ndef compute_factor(df):\n    return df"
    result = evaluate_quant_quality(code=code, backtest_metrics=None)
    assert result.passed is False
