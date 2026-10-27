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
        assert client.get("/health").json() == {"status": "ok"}
        assert client.get("/symbols").json() == {"symbols": ["AAA", "ZZZ"]}
    finally:
        app.dependency_overrides.clear()


def test_analytics_response_and_unknown_symbol(tmp_path):
    path = tmp_path / "prices.csv"
    path.write_text("date,symbol,close\n2026-01-01,AAPL,100\n2026-01-02,AAPL,110\n2026-01-03,AAPL,99\n")
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
