def _load_target():
    import importlib

    module = importlib.import_module("scenarios.data_science.code_safety")
    return module.validate_code_safety, module.SafetyResult


def test_safe_pandas_code_passes():
    validate_code_safety, SafetyResult = _load_target()
    code = 'import pandas as pd\ndf = pd.read_csv("data.csv")'
    result = validate_code_safety(code)
    assert isinstance(result, SafetyResult)
    assert result.safe is True
    assert result.violations == []


def test_safe_numpy_sklearn_code_passes():
    validate_code_safety, SafetyResult = _load_target()
    code = "import numpy as np\nfrom sklearn.linear_model import LinearRegression"
    result = validate_code_safety(code)
    assert isinstance(result, SafetyResult)
    assert result.safe is True
    assert result.violations == []


def test_os_system_rejected():
    validate_code_safety, SafetyResult = _load_target()
    code = 'import os\nos.system("rm -rf /")'
    result = validate_code_safety(code)
    assert isinstance(result, SafetyResult)
    assert result.safe is False
    assert any("os" in violation.lower() for violation in result.violations)


def test_subprocess_rejected():
    validate_code_safety, SafetyResult = _load_target()
    code = 'import subprocess\nsubprocess.run(["ls"])'
    result = validate_code_safety(code)
    assert isinstance(result, SafetyResult)
    assert result.safe is False
    assert any("subprocess" in violation.lower() for violation in result.violations)


def test_eval_rejected():
    validate_code_safety, SafetyResult = _load_target()
    code = 'eval("x = 1")'
    result = validate_code_safety(code)
    assert isinstance(result, SafetyResult)
    assert result.safe is False
    assert any("eval" in violation.lower() for violation in result.violations)


def test_exec_rejected():
    validate_code_safety, SafetyResult = _load_target()
    code = 'exec("import os")'
    result = validate_code_safety(code)
    assert isinstance(result, SafetyResult)
    assert result.safe is False
    assert any("exec" in violation.lower() for violation in result.violations)


def test_open_write_rejected():
    validate_code_safety, SafetyResult = _load_target()
    code = 'open("/etc/passwd", "w")'
    result = validate_code_safety(code)
    assert isinstance(result, SafetyResult)
    assert result.safe is False
    assert any("open" in violation.lower() for violation in result.violations)


def test_import_os_rejected():
    validate_code_safety, SafetyResult = _load_target()
    code = "import os"
    result = validate_code_safety(code)
    assert isinstance(result, SafetyResult)
    assert result.safe is False
    assert any("os" in violation.lower() for violation in result.violations)


def test_nested_dangerous_call_caught():
    validate_code_safety, SafetyResult = _load_target()
    code = """
def run():
    value = 1
    eval('value + 1')
    return value
"""
    result = validate_code_safety(code)
    assert isinstance(result, SafetyResult)
    assert result.safe is False
    assert any("eval" in violation.lower() for violation in result.violations)


def test_multiline_mixed_code_rejected():
    validate_code_safety, SafetyResult = _load_target()
    code = """
import pandas as pd
import numpy as np

df = pd.DataFrame({"x": [1, 2, 3]})
arr = np.array([1, 2, 3])
exec('print(arr)')
"""
    result = validate_code_safety(code)
    assert isinstance(result, SafetyResult)
    assert result.safe is False
    assert result.violations


def test_safe_json_pathlib_allowed():
    validate_code_safety, SafetyResult = _load_target()
    code = "import json\nimport pathlib\nvalue = json.loads('{\"a\": 1}')"
    result = validate_code_safety(code)
    assert isinstance(result, SafetyResult)
    assert result.safe is True
    assert result.violations == []
