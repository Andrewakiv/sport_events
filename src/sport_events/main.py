from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from sport_events.api.router import api_router
from sport_events.database.connection import Database
from sport_events.match_chat.anthropic_model import AnthropicLanguageModel, create_client
from sport_events.match_chat.rate_limit import SlidingWindowRateLimiter
from sport_events.settings import Settings, get_settings


def create_app(
    settings: Settings | None = None,
    database: Database | None = None,
) -> FastAPI:
    resolved_settings = settings or get_settings()
    database_connection = database or Database(resolved_settings.database_url)
    api_key = resolved_settings.anthropic_api_key
    anthropic_client = create_client(api_key.get_secret_value()) if api_key else None

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        await database_connection.close()
        if anthropic_client is not None:
            await anthropic_client.close()

    application = FastAPI(
        title=resolved_settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
    )
    application.state.database = database_connection
    application.state.language_model = (
        AnthropicLanguageModel(anthropic_client) if anthropic_client else None
    )
    application.state.chat_rate_limiter = SlidingWindowRateLimiter(
        resolved_settings.chat_rate_limit_requests,
        resolved_settings.chat_rate_limit_window_seconds,
    )
    application.include_router(api_router, prefix="/api/v1")
    return application


app = create_app()
