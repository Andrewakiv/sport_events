"""HTTP dependency resolution and request-scoped read sessions."""

from collections.abc import AsyncIterator, Callable
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from sport_events.database.connection import Database
from sport_events.football_read.models import FootballMatchReader


def get_database(request: Request) -> Database:
    database: Database = request.app.state.database
    return database


async def get_read_session(
    database: Annotated[Database, Depends(get_database)],
) -> AsyncIterator[AsyncSession]:
    async with database.read_session() as session:
        yield session


def get_match_reader(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_read_session)],
) -> FootballMatchReader:
    factory: Callable[[AsyncSession], FootballMatchReader] = (
        request.app.state.football_match_reader_factory
    )
    return factory(session)
