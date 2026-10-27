"""Application service coordinating price loading and analytics."""
import os
from pathlib import Path

import pandas as pd

from marketlens.analytics.metrics import calculate_metrics
from marketlens.data.loader import DataLoadingError, load_prices

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATA_PATH = PROJECT_ROOT / "data" / "sample_prices.csv"


class UnknownSymbolError(LookupError):
    """Requested symbol is not present in the dataset."""


class AnalyticsService:
    """Load prices from a configured path and compute per-symbol metrics."""

    def __init__(self, data_path: str | Path | None = None):
        configured_path = data_path if data_path is not None else os.getenv("MARKETLENS_DATA_PATH")
        self.data_path = Path(configured_path).expanduser() if configured_path else DEFAULT_DATA_PATH

    def _prices(self) -> pd.DataFrame:
        return load_prices(self.data_path)

    def symbols(self) -> list[str]:
        return sorted(self._prices()["symbol"].unique().tolist())

    def analytics(self, symbol: str) -> dict[str, float | int | str]:
        normalized_symbol = symbol.strip().upper()
        prices = self._prices()
        selected = prices.loc[prices["symbol"] == normalized_symbol]
        if selected.empty:
            raise UnknownSymbolError(f"Unknown symbol: {symbol}")
        return {"symbol": normalized_symbol, **calculate_metrics(selected)}
