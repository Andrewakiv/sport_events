"""HTTP dependency resolution and request-scoped read sessions."""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from sport_events.database.connection import Database
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
