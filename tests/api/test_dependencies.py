from contextlib import asynccontextmanager
from types import TracebackType

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from sport_events.api.dependencies import get_match_queries, get_read_session
from sport_events.database.connection import Database
from sport_events.queries.champions_league_matches import ChampionsLeagueMatchQueries


class SessionContext:
    def __init__(self) -> None:
        self.session = AsyncSession()
        self.closed = False
        self.error: BaseException | None = None

    async def __aenter__(self) -> AsyncSession:
        return self.session

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.error = exc
        await self.session.close()
        self.closed = True


class SessionDatabase:
    def __init__(self, context: SessionContext) -> None:
        self.context = context

    def read_session(self) -> SessionContext:
        return self.context


@pytest.mark.parametrize("fail", [False, True])
async def test_read_session_dependency_cleans_up_on_success_and_failure(fail: bool) -> None:
    context = SessionContext()
    dependency = asynccontextmanager(get_read_session)

    async def invoke() -> None:
        async with dependency(SessionDatabase(context)) as session:  # type: ignore[arg-type]
            assert session is context.session
            assert not context.closed
            if fail:
                raise RuntimeError("request failed")

    if fail:
        with pytest.raises(RuntimeError, match="request failed"):
            await invoke()
        assert isinstance(context.error, RuntimeError)
    else:
        await invoke()
        assert context.error is None
    assert context.closed


async def test_query_dependency_injects_the_provided_session() -> None:
    async with AsyncSession() as session:
        queries = get_match_queries(session)
        assert isinstance(queries, ChampionsLeagueMatchQueries)
        assert queries._session is session


async def test_read_session_isolation_does_not_change_shared_engine() -> None:
    database = Database("postgresql+asyncpg://unused")
    try:
        async with database.read_session() as session:
            assert session.bind is not None
            assert session.bind.get_execution_options()["isolation_level"] == "REPEATABLE READ"
            assert "isolation_level" not in database._engine.get_execution_options()
            assert session.bind.pool is database._engine.pool
    finally:
        await database.close()
