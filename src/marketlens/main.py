"""FastAPI application entry point."""
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from marketlens.api.routes import router

app = FastAPI(title="MarketLens", version="0.1.1", description="Historical stock price risk analytics")
app.include_router(router)
STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def dashboard() -> FileResponse:
    """Serve the single-page dashboard."""
    return FileResponse(STATIC_DIR / "index.html")
