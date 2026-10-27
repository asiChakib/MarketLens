import pytest

from marketlens.data.loader import DataLoadingError
from marketlens.services.analytics_service import AnalyticsService, UnknownSymbolError


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


def test_unknown_symbol():
    service = AnalyticsService()
    service._prices = lambda: __import__("pandas").DataFrame(
        {"date": __import__("pandas").to_datetime(["2026-01-01"]), "symbol": ["AAA"], "close": [1]}
    )
    with pytest.raises(UnknownSymbolError, match="Unknown symbol"):
        service.analytics("NOPE")


def test_invalid_configured_data_is_consistent(tmp_path):
    path = tmp_path / "bad.csv"
    path.write_text("date,symbol\n2026-01-01,A\n")
    with pytest.raises(DataLoadingError, match="Missing required"):
        AnalyticsService(path).symbols()
