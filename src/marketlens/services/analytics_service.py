"""Application service coordinating price loading and analytics."""
import os
from datetime import date
from pathlib import Path

import pandas as pd

from marketlens.analytics.metrics import calculate_metrics
from marketlens.data.loader import DataLoadingError, load_prices

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATA_PATH = PROJECT_ROOT / "data" / "sample_prices.csv"
DATA_DIRECTORY = PROJECT_ROOT / "data"


class UnknownSymbolError(LookupError):
    """Requested symbol is not present in the dataset."""


class UnknownDatasetError(LookupError):
    """Requested dataset is not available in the project data directory."""


class InvalidDateRangeError(ValueError):
    """Requested analytics window has an invalid or empty date range."""


class AnalyticsService:
    """Load prices from a configured path and compute per-symbol metrics."""

    def __init__(self, data_path: str | Path | None = None, dataset: str | None = None):
        configured_path = data_path if data_path is not None else os.getenv("MARKETLENS_DATA_PATH")
        self.data_path = Path(configured_path).expanduser() if configured_path else DEFAULT_DATA_PATH
        self.dataset = dataset

    @property
    def default_dataset(self) -> str:
        """Return the dataset id corresponding to the configured default path."""
        data_directory = DATA_DIRECTORY.resolve()
        configured_path = self.data_path.resolve()
        if configured_path.parent == data_directory:
            return configured_path.name
        return "__default__"

    def datasets(self) -> list[dict[str, str]]:
        """List CSV datasets available in the data directory."""
        data_directory = DATA_DIRECTORY.resolve()
        options = []
        for path in sorted(data_directory.glob("*.csv"), key=lambda item: item.name.casefold()):
            resolved_path = path.resolve()
            if resolved_path.parent != data_directory or not resolved_path.is_file():
                continue
            label = path.stem.replace("_", " ").replace("-", " ").title()
            options.append({"id": path.name, "name": label})

        default_id = self.default_dataset
        if default_id == "__default__":
            options.append({"id": default_id, "name": f"Configured dataset ({self.data_path.name})"})
        elif not any(option["id"] == default_id for option in options):
            label = self.data_path.stem.replace("_", " ").replace("-", " ").title()
            options.append({"id": default_id, "name": label})
        return options

    def _selected_data_path(self) -> Path:
        """Resolve a requested dataset id without allowing arbitrary file paths."""
        if self.dataset is None or self.dataset == "__default__":
            return self.data_path
        data_directory = DATA_DIRECTORY.resolve()
        if Path(self.dataset).name != self.dataset or Path(self.dataset).suffix.lower() != ".csv":
            raise UnknownDatasetError(f"Unknown dataset: {self.dataset}")
        selected_path = (data_directory / self.dataset).resolve()
        if selected_path.parent != data_directory or not selected_path.is_file():
            raise UnknownDatasetError(f"Unknown dataset: {self.dataset}")
        return selected_path

    def _prices(self) -> pd.DataFrame:
        return load_prices(self._selected_data_path())

    def symbols(self) -> list[str]:
        return sorted(self._prices()["symbol"].unique().tolist())

    def analytics(
        self,
        symbol: str,
        start: date | None = None,
        end: date | None = None,
    ) -> dict[str, float | int | str]:
        if start is not None and end is not None and start > end:
            raise InvalidDateRangeError("The start date must be on or before the end date.")
        normalized_symbol = symbol.strip().upper()
        prices = self._prices()
        selected = prices.loc[prices["symbol"] == normalized_symbol]
        if selected.empty:
            raise UnknownSymbolError(f"Unknown symbol: {symbol}")
        if start is not None:
            selected = selected.loc[selected["date"] >= pd.Timestamp(start)]
        if end is not None:
            selected = selected.loc[selected["date"] <= pd.Timestamp(end)]
        if selected.empty:
            raise InvalidDateRangeError("No price observations fall within the selected date window.")
        return {"symbol": normalized_symbol, **calculate_metrics(selected)}

    def prices(self, symbol: str) -> dict[str, str | list[dict[str, str | float]]]:
        """Return a symbol's dated closing prices in chronological order."""
        normalized_symbol = symbol.strip().upper()
        selected = self._prices().loc[lambda frame: frame["symbol"] == normalized_symbol]
        if selected.empty:
            raise UnknownSymbolError(f"Unknown symbol: {symbol}")
        selected = selected.sort_values("date")
        observations = [
            {"date": date.strftime("%Y-%m-%d"), "close": float(close)}
            for date, close in zip(selected["date"], selected["close"], strict=True)
        ]
        return {"symbol": normalized_symbol, "prices": observations}
