"""Pydantic response models."""
from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    status: str = "ok"


class SymbolsResponse(BaseModel):
    symbols: list[str]


class DatasetOption(BaseModel):
    id: str
    name: str


class DatasetsResponse(BaseModel):
    datasets: list[DatasetOption]
    default_dataset: str


class PriceObservation(BaseModel):
    date: str
    close: float = Field(gt=0)


class PricesResponse(BaseModel):
    symbol: str
    prices: list[PriceObservation]


class AnalyticsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str
    total_return: float
    annualized_volatility: float = Field(ge=0)
    maximum_drawdown: float = Field(le=0)
    mean_daily_return: float
    observations: int = Field(ge=2)


class ErrorResponse(BaseModel):
    detail: str
