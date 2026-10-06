from contextlib import asynccontextmanager
from types import TracebackType

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from sport_events.api.dependencies import get_match_reader, get_read_session
from sport_events.database.connection import Database
from sport_events.main import create_app
from sport_events.queries.champions_league_matches import SqlAlchemyChampionsLeagueMatchReader


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


async def test_application_factory_injects_the_provided_session() -> None:
    app = create_app()
    request = Request({"type": "http", "app": app})
    async with AsyncSession() as session:
        reader = get_match_reader(request, session)
        assert isinstance(reader, SqlAlchemyChampionsLeagueMatchReader)
        assert reader._session is session
        assert app.state.football_match_reader_factory is SqlAlchemyChampionsLeagueMatchReader
    await app.state.database.close()


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
