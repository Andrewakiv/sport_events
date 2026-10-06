from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from sport_events.api.router import api_router
from sport_events.database.connection import Database
from sport_events.settings import Settings, get_settings


def create_app(
    settings: Settings | None = None,
    database: Database | None = None,
) -> FastAPI:
    resolved_settings = settings or get_settings()
    database_connection = database or Database(resolved_settings.database_url)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        await database_connection.close()

    application = FastAPI(
        title=resolved_settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
    )
    application.state.database = database_connection
    application.include_router(api_router, prefix="/api/v1")
    return application


app = create_app()
