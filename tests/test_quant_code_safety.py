"""Tests for code safety validator (TDD)."""

import pytest

from scenarios.quant.code_safety import validate_code_safety


class TestSyntaxErrors:
    def test_invalid_syntax_rejected(self):
        ok, reason = validate_code_safety("def foo(:\n    pass")
        assert not ok
        assert "SyntaxError" in reason

    def test_valid_syntax_passes(self):
        ok, reason = validate_code_safety("x = 1 + 2")
        assert ok
        assert reason is None


class TestBlockedImports:
    def test_os_import_blocked(self):
        ok, reason = validate_code_safety("import os")
        assert not ok
        assert "os" in reason

    def test_subprocess_blocked(self):
        ok, reason = validate_code_safety("import subprocess")
        assert not ok
        assert "subprocess" in reason

    def test_sys_blocked(self):
        ok, reason = validate_code_safety("from sys import argv")
        assert not ok
        assert "sys" in reason

    def test_socket_blocked(self):
        ok, reason = validate_code_safety("import socket")
        assert not ok

    def test_pathlib_blocked(self):
        ok, reason = validate_code_safety("from pathlib import Path")
        assert not ok


class TestSafeImports:
    def test_numpy_allowed(self):
        ok, reason = validate_code_safety("import numpy as np")
        assert ok

    def test_pandas_allowed(self):
        ok, reason = validate_code_safety("import pandas as pd")
        assert ok

    def test_math_allowed(self):
        ok, reason = validate_code_safety("import math")
        assert ok

    def test_from_numpy_allowed(self):
        ok, reason = validate_code_safety("from numpy import array")
        assert ok


class TestUnknownImports:
    def test_unknown_package_rejected(self):
        ok, reason = validate_code_safety("import requests")
        assert not ok

    def test_scikit_learn_rejected(self):
        ok, reason = validate_code_safety("from sklearn.linear_model import LinearRegression")
        assert not ok


class TestDangerousBuiltins:
    def test_exec_call_blocked(self):
        ok, reason = validate_code_safety("exec('import os')")
        assert not ok
        assert "exec" in reason

    def test_eval_call_blocked(self):
        ok, reason = validate_code_safety("result = eval('1+1')")
        assert not ok
        assert "eval" in reason

    def test_open_call_blocked(self):
        ok, reason = validate_code_safety("f = open('file.txt')")
        assert not ok
        assert "open" in reason

    def test_dunder_import_blocked(self):
        ok, reason = validate_code_safety("mod = __import__('os')")
        assert not ok

    def test_globals_call_blocked(self):
        ok, reason = validate_code_safety("g = globals()")
        assert not ok


class TestLegitimateFactorCode:
    def test_momentum_factor_passes(self):
        code = """
import numpy as np
import pandas as pd

def compute_factor(df):
    return df.groupby('stock')['close'].pct_change(20)
"""
        ok, reason = validate_code_safety(code)
        assert ok, reason

    def test_rolling_zscore_passes(self):
        code = """
import pandas as pd

def compute_factor(df):
    r = df.groupby('stock')['close'].pct_change()
    return r.groupby(df['stock']).transform(lambda x: (x - x.rolling(20).mean()) / x.rolling(20).std())
"""
        ok, reason = validate_code_safety(code)
        assert ok, reason
