"""Tests for RewardCalculator in MCTS backpropagation (FC-2).

Validates score-based (tanh normalization) and decision-based modes
against official RDAgent reward computation.
"""

import math

import pytest

from exploration_manager.reward import RewardCalculator


# Score-Based Mode Tests
def test_positive_direction_score_based():
    """tanh(0.8) * 1 ≈ 0.6640"""
    r = RewardCalculator(mode="score_based", direction=1)
    result = r.calculate(score=0.8, decision=None)
    assert abs(result - math.tanh(0.8)) < 1e-6


def test_negative_direction_score_based():
    """tanh(0.8) * -1 for smaller_is_better"""
    r = RewardCalculator(mode="score_based", direction=-1)
    result = r.calculate(score=0.8, decision=None)
    assert abs(result - (-math.tanh(0.8))) < 1e-6


def test_zero_score_score_based():
    """tanh(0) = 0"""
    r = RewardCalculator(mode="score_based", direction=1)
    assert r.calculate(score=0.0, decision=None) == 0.0


def test_large_score_saturates():
    """tanh(10) ≈ 1.0 (saturation)"""
    r = RewardCalculator(mode="score_based", direction=1)
    result = r.calculate(score=10.0, decision=None)
    assert result > 0.999


def test_score_none_falls_back_to_decision_true():
    """score_based mode with score=None should fall back to decision_based"""
    r = RewardCalculator(mode="score_based", direction=1)
    assert r.calculate(score=None, decision=True) == 1.0


def test_score_none_falls_back_to_decision_false():
    """score_based mode with score=None should fall back to decision_based"""
    r = RewardCalculator(mode="score_based", direction=1)
    assert r.calculate(score=None, decision=False) == 0.0


# Decision-Based Mode Tests
def test_true_decision_decision_based():
    """decision_based mode returns 1.0 for True"""
    r = RewardCalculator(mode="decision_based")
    assert r.calculate(score=None, decision=True) == 1.0


def test_false_decision_decision_based():
    """decision_based mode returns 0.0 for False"""
    r = RewardCalculator(mode="decision_based")
    assert r.calculate(score=None, decision=False) == 0.0


def test_decision_ignores_score_high():
    """In decision_based mode, score is ignored (high score, False decision)"""
    r = RewardCalculator(mode="decision_based")
    assert r.calculate(score=0.99, decision=False) == 0.0


def test_decision_ignores_score_low():
    """In decision_based mode, score is ignored (low score, True decision)"""
    r = RewardCalculator(mode="decision_based")
    assert r.calculate(score=0.01, decision=True) == 1.0


# Edge Cases & Defaults
def test_both_none_returns_zero():
    """When both score and decision are None, return 0.0"""
    r = RewardCalculator()
    assert r.calculate(score=None, decision=None) == 0.0


def test_default_mode_is_score_based():
    """Default mode should be score_based"""
    r = RewardCalculator()
    result = r.calculate(score=0.5, decision=None)
    assert abs(result - math.tanh(0.5)) < 1e-6


def test_default_direction_is_positive():
    """Default direction should be 1 (positive)"""
    r = RewardCalculator()
    result = r.calculate(score=0.5, decision=None)
    assert result > 0


def test_negative_score_score_based():
    """tanh handles negative scores correctly"""
    r = RewardCalculator(mode="score_based", direction=1)
    result = r.calculate(score=-0.5, decision=None)
    assert abs(result - math.tanh(-0.5)) < 1e-6
    assert result < 0  # negative score should produce negative reward
