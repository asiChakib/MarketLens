"""CSV loading and strict validation for historical prices."""
from pathlib import Path

import numpy as np
import pandas as pd

REQUIRED_COLUMNS = {"date", "symbol", "close"}


class DataLoadingError(ValueError):
    """Raised when a price dataset cannot be read or validated."""


def load_prices(path: str | Path) -> pd.DataFrame:
    """Load a CSV and return normalized rows sorted by symbol and date."""
    source = Path(path).expanduser()
    if not source.is_file():
        raise DataLoadingError(f"Price data file does not exist: {source}")
    try:
        frame = pd.read_csv(source)
    except pd.errors.EmptyDataError as exc:
        raise DataLoadingError("Price dataset is empty") from exc
    except (OSError, pd.errors.ParserError, UnicodeError) as exc:
        raise DataLoadingError(f"Could not read price data file {source}: {exc}") from exc

    missing = sorted(REQUIRED_COLUMNS - set(frame.columns))
    if missing:
        raise DataLoadingError(f"Missing required column(s): {', '.join(missing)}")
    frame = frame[["date", "symbol", "close"]].copy()
    if frame.empty:
        raise DataLoadingError("Price dataset is empty")

    parsed_dates = pd.to_datetime(frame["date"], errors="coerce", format="mixed", utc=True)
    # pandas 2.0 compatibility: format='mixed' was introduced in pandas 2.0.
    invalid_dates = parsed_dates.isna()
    if invalid_dates.any():
        row = int(np.flatnonzero(invalid_dates.to_numpy())[0]) + 2
        raise DataLoadingError(f"Invalid date at CSV row {row}: {frame.iloc[row - 2]['date']!r}")
    frame["date"] = parsed_dates.dt.tz_convert(None)

    symbols = frame["symbol"]
    invalid_symbols = symbols.isna() | ~symbols.map(lambda value: isinstance(value, str) and bool(value.strip()))
    if invalid_symbols.any():
        row = int(np.flatnonzero(invalid_symbols.to_numpy())[0]) + 2
        raise DataLoadingError(f"Symbol must be a non-empty string at CSV row {row}")
    frame["symbol"] = symbols.str.strip().str.upper()

    prices = pd.to_numeric(frame["close"], errors="coerce")
    invalid_prices = prices.isna() | ~np.isfinite(prices) | (prices <= 0)
    if invalid_prices.any():
        row = int(np.flatnonzero(invalid_prices.to_numpy())[0]) + 2
        raise DataLoadingError(f"Close must be a finite, positive number at CSV row {row}")
    frame["close"] = prices.astype(float)

    duplicates = frame.duplicated(["date", "symbol"], keep=False)
    if duplicates.any():
        duplicate = frame.loc[duplicates, ["date", "symbol"]].iloc[0]
        raise DataLoadingError(f"Duplicate (date, symbol) record: {duplicate['date'].date()} {duplicate['symbol']}")
    return frame.sort_values(["symbol", "date"], kind="mergesort").reset_index(drop=True)
