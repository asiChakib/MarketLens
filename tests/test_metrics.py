import numpy as np
import pandas as pd
import pytest

from marketlens.analytics.metrics import InsufficientObservationsError, calculate_metrics, daily_returns


def frame(values):
    return pd.DataFrame({"date": pd.date_range("2026-01-01", periods=len(values)), "close": values})


def test_returns_and_metrics_for_100_110_99():
    prices = frame([100, 110, 99])
    assert daily_returns(prices).tolist() == pytest.approx([0.1, -0.1])
    metrics = calculate_metrics(prices)
    assert metrics["total_return"] == pytest.approx(-0.01)
    assert metrics["annualized_volatility"] == pytest.approx(np.std([0.1, -0.1], ddof=1) * np.sqrt(252))
    assert metrics["mean_daily_return"] == pytest.approx(0.0)
    assert metrics["maximum_drawdown"] == pytest.approx(-0.1)
    assert metrics["observations"] == 2


def test_drawdown_during_recovery_and_flat_prices():
    assert calculate_metrics(frame([100, 80, 90]))["maximum_drawdown"] == pytest.approx(-0.2)
    flat = calculate_metrics(frame([10, 10, 10]))
    assert flat["annualized_volatility"] == 0
    assert flat["maximum_drawdown"] == 0


def test_requires_two_daily_returns():
    with pytest.raises(InsufficientObservationsError, match="At least two"):
        calculate_metrics(frame([100, 101]))


def test_symbols_calculated_independently():
    a = pd.DataFrame({"date": pd.date_range("2026-01-01", periods=3), "close": [10, 20, 10]})
    b = pd.DataFrame({"date": pd.date_range("2026-01-01", periods=3), "close": [100, 101, 102]})
    assert calculate_metrics(a)["total_return"] == pytest.approx(0)
    assert calculate_metrics(b)["total_return"] == pytest.approx(0.02)
