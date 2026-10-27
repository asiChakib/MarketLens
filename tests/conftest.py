import pandas as pd
import pytest
from fastapi.testclient import TestClient

from marketlens.main import app


@pytest.fixture
def prices_frame():
    return pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-01-01", "2026-01-02", "2026-01-03"]),
            "symbol": ["AAA"] * 3,
            "close": [100.0, 110.0, 99.0],
        }
    )


@pytest.fixture
def client():
    return TestClient(app)
