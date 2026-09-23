from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status

from sport_events.api.schemas.health import HealthResponse
from sport_events.database.connection import Database

router = APIRouter(prefix="/health", tags=["health"])


def get_database(request: Request) -> Database:
    database: Database = request.app.state.database
    return database


@router.get("/live", response_model=HealthResponse)
async def liveness() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/ready", response_model=HealthResponse)
async def readiness(
    response: Response,
    database: Annotated[Database, Depends(get_database)],
) -> HealthResponse:
    if await database.is_available():
        return HealthResponse(status="ok")

    response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return HealthResponse(status="unavailable")
