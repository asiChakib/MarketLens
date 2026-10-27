from datetime import date

import pytest

from marketlens.data.loader import DataLoadingError
from marketlens.services.analytics_service import (
    AnalyticsService,
    InvalidDateRangeError,
    UnknownSymbolError,
)


def test_service_metrics_symbols_and_configured_path(tmp_path):
    path = tmp_path / "prices.csv"
    path.write_text(
        "date,symbol,close\n2026-01-01,ZZZ,100\n2026-01-02,ZZZ,110\n2026-01-03,ZZZ,99\n"
        "2026-01-01,AAA,1\n2026-01-02,AAA,2\n2026-01-03,AAA,3\n"
    )
    service = AnalyticsService(path)
    assert service.data_path == path
    assert service.symbols() == ["AAA", "ZZZ"]
    assert service.analytics("zzz")["total_return"] == pytest.approx(-0.01)
    assert service.prices("zzz") == {
        "symbol": "ZZZ",
        "prices": [
            {"date": "2026-01-01", "close": 100.0},
            {"date": "2026-01-02", "close": 110.0},
            {"date": "2026-01-03", "close": 99.0},
        ],
    }


def test_unknown_symbol():
    service = AnalyticsService()
    service._prices = lambda: __import__("pandas").DataFrame(
        {"date": __import__("pandas").to_datetime(["2026-01-01"]), "symbol": ["AAA"], "close": [1]}
    )
    with pytest.raises(UnknownSymbolError, match="Unknown symbol"):
        service.analytics("NOPE")


def test_analytics_filters_to_inclusive_date_window(tmp_path):
    path = tmp_path / "prices.csv"
    path.write_text(
        "date,symbol,close\n"
        "2026-01-01,AAA,100\n"
        "2026-01-02,AAA,110\n"
        "2026-01-03,AAA,121\n"
        "2026-01-04,AAA,132\n"
        "2026-01-05,AAA,150\n"
    )

    metrics = AnalyticsService(path).analytics(
        "AAA", start=date(2026, 1, 2), end=date(2026, 1, 4)
    )

    assert metrics["total_return"] == pytest.approx(0.2)
    assert metrics["observations"] == 2


def test_analytics_rejects_reversed_or_empty_date_window(tmp_path):
    path = tmp_path / "prices.csv"
    path.write_text(
        "date,symbol,close\n"
        "2026-01-01,AAA,100\n"
        "2026-01-02,AAA,110\n"
        "2026-01-03,AAA,121\n"
    )
    service = AnalyticsService(path)

    with pytest.raises(InvalidDateRangeError, match="on or before"):
        service.analytics("AAA", start=date(2026, 1, 3), end=date(2026, 1, 2))
    with pytest.raises(InvalidDateRangeError, match="No price observations"):
        service.analytics("AAA", start=date(2026, 2, 1), end=date(2026, 2, 28))


def test_invalid_configured_data_is_consistent(tmp_path):
    path = tmp_path / "bad.csv"
    path.write_text("date,symbol\n2026-01-01,A\n")
    with pytest.raises(DataLoadingError, match="Missing required"):
        AnalyticsService(path).symbols()
