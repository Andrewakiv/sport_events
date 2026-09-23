import os

import pytest

from sport_events.database.connection import Database


@pytest.mark.integration
async def test_database_connection() -> None:
    database_url = os.getenv("SPORT_EVENTS_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("SPORT_EVENTS_TEST_DATABASE_URL is not configured")

    database = Database(database_url)
    try:
        assert await database.is_available() is True
    finally:
        await database.close()
