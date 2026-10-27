"""FastAPI application entry point."""
from fastapi import FastAPI

from marketlens.api.routes import router

app = FastAPI(title="MarketLens", version="0.1.0", description="Historical stock price risk analytics")
app.include_router(router)
