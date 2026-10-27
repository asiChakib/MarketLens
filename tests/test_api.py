from fastapi.testclient import TestClient
import pytest

from marketlens.api.routes import get_service
from marketlens.main import app
from marketlens.services.analytics_service import AnalyticsService


def test_health_and_symbols(tmp_path):
    path = tmp_path / "prices.csv"
    path.write_text(
        "date,symbol,close\n2026-01-01,ZZZ,100\n2026-01-02,ZZZ,110\n2026-01-03,ZZZ,99\n"
        "2026-01-01,AAA,200\n2026-01-02,AAA,204\n2026-01-03,AAA,202\n"
    )
    app.dependency_overrides[get_service] = lambda: AnalyticsService(path)
    try:
        client = TestClient(app)
        home = client.get("/")
        assert home.status_code == 200
        assert "MarketLens" in home.text
        assert client.get("/static/app.js").status_code == 200
        assert client.get("/static/styles.css").status_code == 200
        assert client.get("/health").json() == {"status": "ok"}
        assert client.get("/symbols").json() == {"symbols": ["AAA", "ZZZ"]}
    finally:
        app.dependency_overrides.clear()


def test_analytics_response_and_unknown_symbol(tmp_path):
    path = tmp_path / "prices.csv"
    path.write_text("date,symbol,close\n2026-01-02,AAPL,110\n2026-01-01,AAPL,100\n2026-01-03,AAPL,99\n")
    app.dependency_overrides[get_service] = lambda: AnalyticsService(path)
    try:
        client = TestClient(app)
        response = client.get("/analytics/AAPL")
        assert response.status_code == 200
        body = response.json()
        assert body["symbol"] == "AAPL"
        assert body["total_return"] == pytest.approx(-0.01)
        assert body["observations"] == 2
        assert set(body) == {
            "symbol", "total_return", "annualized_volatility", "maximum_drawdown", "mean_daily_return", "observations"
        }
        assert client.get("/analytics/NOPE").status_code == 404
        prices = client.get("/prices/AAPL")
        assert prices.status_code == 200
        assert prices.json() == {
            "symbol": "AAPL",
            "prices": [
                {"date": "2026-01-01", "close": 100.0},
                {"date": "2026-01-02", "close": 110.0},
                {"date": "2026-01-03", "close": 99.0},
            ],
        }
        assert client.get("/prices/NOPE").status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_analytics_date_window_and_invalid_ranges(tmp_path):
    path = tmp_path / "prices.csv"
    path.write_text(
        "date,symbol,close\n"
        "2026-01-01,AAA,100\n"
        "2026-01-02,AAA,110\n"
        "2026-01-03,AAA,121\n"
        "2026-01-04,AAA,132\n"
        "2026-01-05,AAA,150\n"
    )
    app.dependency_overrides[get_service] = lambda: AnalyticsService(path)
    try:
        client = TestClient(app)
        response = client.get(
            "/analytics/AAA", params={"start": "2026-01-02", "end": "2026-01-04"}
        )
        assert response.status_code == 200
        assert response.json()["total_return"] == pytest.approx(0.2)
        assert response.json()["observations"] == 2

        reversed_window = client.get(
            "/analytics/AAA", params={"start": "2026-01-04", "end": "2026-01-02"}
        )
        assert reversed_window.status_code == 422
        assert "on or before" in reversed_window.json()["detail"]

        empty_window = client.get(
            "/analytics/AAA", params={"start": "2026-02-01", "end": "2026-02-28"}
        )
        assert empty_window.status_code == 422
        assert "No price observations" in empty_window.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_bad_server_data_returns_structured_error_without_traceback(tmp_path):
    path = tmp_path / "bad.csv"
    path.write_text("date,symbol\n2026-01-01,A\n")
    app.dependency_overrides[get_service] = lambda: AnalyticsService(path)
    try:
        response = TestClient(app).get("/symbols")
        assert response.status_code == 500
        assert "Missing required column" in response.json()["detail"]
        assert "Traceback" not in response.text
    finally:
        app.dependency_overrides.clear()


