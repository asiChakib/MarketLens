"""Pure financial calculations independent of the API layer."""
import numpy as np
import pandas as pd

TRADING_DAYS_PER_YEAR = 252


class InsufficientObservationsError(ValueError):
    """Raised when a metric cannot be calculated from available returns."""


def daily_returns(prices: pd.DataFrame) -> pd.Series:
    """Compute simple returns for a single symbol's chronologically sorted prices."""
    ordered = prices.sort_values("date")
    return ordered["close"].astype(float).pct_change().dropna().reset_index(drop=True)


def calculate_metrics(prices: pd.DataFrame) -> dict[str, float | int]:
    """Calculate price return, sample annualized volatility, mean and drawdown."""
    ordered = prices.sort_values("date")
    returns = daily_returns(ordered)
    if len(returns) < 2:
        raise InsufficientObservationsError(
            f"At least two daily returns are required; found {len(returns)}"
        )
    close = ordered["close"].astype(float)
    return {
        "total_return": float(close.iloc[-1] / close.iloc[0] - 1.0),
        "annualized_volatility": float(returns.std(ddof=1) * np.sqrt(TRADING_DAYS_PER_YEAR)),
        "maximum_drawdown": float((close / close.cummax() - 1.0).min()),
        "mean_daily_return": float(returns.mean()),
        "observations": int(len(returns)),
    }
