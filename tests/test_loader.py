import pandas as pd
import pytest

from marketlens.data.loader import DataLoadingError, load_prices


def test_loads_parses_and_sorts(tmp_path):
    path = tmp_path / "prices.csv"
    path.write_text("date,symbol,close\n2026-01-02,aaa,110\n2026-01-01,aaa,100\n")
    frame = load_prices(path)
    assert list(frame["symbol"]) == ["AAA", "AAA"]
    assert list(frame["close"]) == [100.0, 110.0]
    assert pd.api.types.is_datetime64_any_dtype(frame["date"])


@pytest.mark.parametrize(
    "contents, message",
    [
        ("date,symbol\n2026-01-01,A\n", "Missing required column.*close"),
        ("date,symbol,close\nnot-a-date,A,10\n", "Invalid date"),
        ("date,symbol,close\n2026-01-01,A,nope\n", "finite, positive"),
        ("date,symbol,close\n2026-01-01,A,0\n", "finite, positive"),
        ("date,symbol,close\n2026-01-01,A,-1\n", "finite, positive"),
        ("date,symbol,close\n2026-01-01,A,inf\n", "finite, positive"),
        ("date,symbol,close\n2026-01-01, ,10\n", "non-empty string"),
        ("date,symbol,close\n", "empty"),
    ],
)
def test_rejects_invalid_data(tmp_path, contents, message):
    path = tmp_path / "prices.csv"
    path.write_text(contents)
    with pytest.raises(DataLoadingError, match=message):
        load_prices(path)


def test_rejects_duplicate_date_symbol(tmp_path):
    path = tmp_path / "prices.csv"
    path.write_text("date,symbol,close\n2026-01-01,A,10\n2026-01-01,A,11\n")
    with pytest.raises(DataLoadingError, match="Duplicate"):
        load_prices(path)


def test_missing_file_has_clear_error(tmp_path):
    with pytest.raises(DataLoadingError, match="does not exist"):
        load_prices(tmp_path / "missing.csv")
