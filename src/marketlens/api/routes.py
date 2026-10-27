"""HTTP endpoints for MarketLens."""
from fastapi import APIRouter, Depends, HTTPException, status

from marketlens.analytics.metrics import InsufficientObservationsError
from marketlens.data.loader import DataLoadingError
from marketlens.models.schemas import AnalyticsResponse, ErrorResponse, HealthResponse, SymbolsResponse
from marketlens.services.analytics_service import AnalyticsService, UnknownSymbolError

router = APIRouter()


def get_service() -> AnalyticsService:
    return AnalyticsService()


def _data_error(exc: DataLoadingError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Price data unavailable: {exc}")


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse()


@router.get("/symbols", response_model=SymbolsResponse, responses={500: {"model": ErrorResponse}})
def symbols(service: AnalyticsService = Depends(get_service)) -> SymbolsResponse:
    try:
        return SymbolsResponse(symbols=service.symbols())
    except DataLoadingError as exc:
        raise _data_error(exc) from exc


@router.get(
    "/analytics/{symbol}",
    response_model=AnalyticsResponse,
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
def analytics(symbol: str, service: AnalyticsService = Depends(get_service)) -> AnalyticsResponse:
    try:
        return AnalyticsResponse(**service.analytics(symbol))
    except UnknownSymbolError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InsufficientObservationsError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except DataLoadingError as exc:
        raise _data_error(exc) from exc
