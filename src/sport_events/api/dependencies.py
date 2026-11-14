"""HTTP dependency resolution and request-scoped read sessions."""

import math
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from sport_events.database.connection import Database
from sport_events.match_chat.agent import MatchChatAgent
from sport_events.match_chat.conversation import LanguageModel
from sport_events.match_chat.rate_limit import SlidingWindowRateLimiter
from sport_events.match_chat.tools import ChampionsLeagueTools
from sport_events.queries.champions_league_matches import ChampionsLeagueMatchQueries


def get_database(request: Request) -> Database:
    database: Database = request.app.state.database
    return database


async def get_read_session(
    database: Annotated[Database, Depends(get_database)],
) -> AsyncIterator[AsyncSession]:
    async with database.read_session() as session:
        yield session


def get_match_queries(
    session: Annotated[AsyncSession, Depends(get_read_session)],
) -> ChampionsLeagueMatchQueries:
    return ChampionsLeagueMatchQueries(session)


def get_chat_rate_limiter(request: Request) -> SlidingWindowRateLimiter:
    limiter: SlidingWindowRateLimiter = request.app.state.chat_rate_limiter
    return limiter


def enforce_chat_rate_limit(
    request: Request,
    limiter: Annotated[SlidingWindowRateLimiter, Depends(get_chat_rate_limiter)],
) -> None:
    client = request.client.host if request.client else "unknown"
    retry_after = limiter.check(client)
    if retry_after is not None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests",
            headers={"Retry-After": str(max(1, math.ceil(retry_after)))},
        )


def get_language_model(request: Request) -> LanguageModel:
    model: LanguageModel | None = request.app.state.language_model
    if model is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="chat_unavailable"
        )
    return model


def get_match_chat_agent(
    model: Annotated[LanguageModel, Depends(get_language_model)],
    queries: Annotated[ChampionsLeagueMatchQueries, Depends(get_match_queries)],
) -> MatchChatAgent:
    return MatchChatAgent(model, ChampionsLeagueTools(queries), lambda: datetime.now(UTC).date())
