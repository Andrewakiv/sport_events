from types import TracebackType
from typing import Any

import pytest
from sqlalchemy.exc import SQLAlchemyError

from sport_events.database import connection as connection_module
from sport_events.database.connection import Database


class FakeConnection:
    def __init__(self, error: SQLAlchemyError | None = None) -> None:
        self.error = error
        self.executed = False

    async def execute(self, _: object) -> None:
        self.executed = True
        if self.error is not None:
            raise self.error


class FakeConnectionContext:
    def __init__(self, connection: FakeConnection) -> None:
        self.connection = connection

    async def __aenter__(self) -> FakeConnection:
        return self.connection

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None


class FakeEngine:
    def __init__(self, connection: FakeConnection) -> None:
        self.connection_instance = connection
        self.disposed = False

    def connect(self) -> FakeConnectionContext:
        return FakeConnectionContext(self.connection_instance)

    async def dispose(self) -> None:
        self.disposed = True


def build_database(monkeypatch: pytest.MonkeyPatch, engine: FakeEngine) -> Database:
    def create_engine(*_args: object, **_kwargs: object) -> Any:
        return engine

    monkeypatch.setattr(connection_module, "create_async_engine", create_engine)
    return Database("postgresql+asyncpg://unused")


async def test_reports_available_and_closes_engine(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = FakeEngine(FakeConnection())
    database = build_database(monkeypatch, engine)

    assert await database.is_available() is True
    await database.close()

    assert engine.connection_instance.executed is True
    assert engine.disposed is True


async def test_reports_unavailable_on_sqlalchemy_error(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = FakeEngine(FakeConnection(SQLAlchemyError("database unavailable")))
    database = build_database(monkeypatch, engine)

    assert await database.is_available() is False
