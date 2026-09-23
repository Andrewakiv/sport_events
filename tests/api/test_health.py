from collections.abc import AsyncIterator

from httpx import ASGITransport, AsyncClient

from sport_events.main import create_app


class StubDatabase:
    def __init__(self, available: bool) -> None:
        self.available = available
        self.closed = False

    async def is_available(self) -> bool:
        return self.available

    async def close(self) -> None:
        self.closed = True


async def client_for(database: StubDatabase) -> AsyncIterator[AsyncClient]:
    app = create_app(database=database)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    await database.close()


async def test_liveness() -> None:
    database = StubDatabase(available=True)
    async for client in client_for(database):
        response = await client.get("/api/v1/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_readiness_when_database_is_available() -> None:
    async for client in client_for(StubDatabase(available=True)):
        response = await client.get("/api/v1/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_readiness_when_database_is_unavailable() -> None:
    async for client in client_for(StubDatabase(available=False)):
        response = await client.get("/api/v1/health/ready")

    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}
