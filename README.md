# MarketLens

MarketLens is a small Python service that validates historical closing prices, calculates basic per-symbol risk metrics, and serves them through a REST API. The included CSV contains illustrative data only; it is not live market data.

## Requirements and installation

Python 3.10 or newer and pip are required. From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

On Windows PowerShell, activate with `.venv\Scripts\Activate.ps1`.

## Run

```bash
uvicorn marketlens.main:app --reload
```
see more in **Tests**

The API is available at `http://127.0.0.1:8000/{ROUTE}`.

 By default, data is read from the repository's `data/sample_prices.csv`. Set `MARKETLENS_DATA_PATH` to a CSV path to use another dataset. Relative paths are resolved from the process working directory; the default path is anchored to the installed project source.

## API ROUTES

- `GET /health` — returns `{"status":"ok"}` checking the health of the application.
- `GET /symbols` — returns the symbols of the dataset in sorted order.
- `GET /analytics/{symbol}` — returns metrics for a symbol (SYMBOL is uppercase e.g. AAPL).

Unknown symbols return 404. Invalid or unavailable data returns a structured 500 response. If there are fewer than two daily returns (three price observations), analytics returns 422 because sample volatility cannot be calculated reliably.

## Data and calculations

MarketLens validates and normalizes historical price data before calculating performance and risk metrics. The input CSV must contain `date`, `symbol`, and `close` columns. Invalid data, duplicate records, and empty datasets are rejected.

The API provides daily and total returns, mean daily return, annualized volatility, and maximum drawdown. Metrics are calculated independently for each symbol using its available historical observations.

For more details, see:
- [Rate of Return](https://www.investopedia.com/terms/r/rateofreturn.asp) — understanding price returns.
- [Standard Deviation](https://www.investopedia.com/terms/s/standarddeviation.asp) — measuring return variability.
- [Maximum Drawdown](https://www.investopedia.com/terms/m/maximum-drawdown-mdd.asp) — measuring peak-to-trough declines.

See the source code and tests for the exact formulas, validation rules, and calculation conventions used by MarketLens.

## Design

The `data` package owns CSV parsing and validation, `analytics` contains framework-independent formulas, `services` coordinates loading and per-symbol selection, `models` defines response schemas, and `api` exposes thin FastAPI routes. Data-loading failures, unknown symbols, and insufficient history are mapped to structured HTTP errors.

## Tests

For now, there is only unit tests for the analytics (and symbols retrieval and health checks) and can be runned with:

```bash
pytest -v
```

As of next iteration, the UI will be built, however, you can still test in the browser with
```bash
uvicorn marketlens.main:app --reload
```
then, you'll see a line
```bash
INFO:      Uvicorn running on http://{IP:PORT}
```
you won't see anything interesting, yet, add the the routes manually, 
for example:
``` 
http://{IP:PORT}/analytics/AAPL
```