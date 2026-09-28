"""Manual Champions League season synchronization command."""

import argparse
import asyncio

import httpx
from sqlalchemy.ext.asyncio import create_async_engine

from sport_events.database.football_sync import (
    PostgresSeasonSnapshotStore,
    PostgresSeasonSyncLock,
)
from sport_events.football_data.client import FootballDataClient
from sport_events.football_data.sync_source import FootballDataChampionsLeagueSource
from sport_events.football_sync.operation import SynchronizeChampionsLeagueSeason
from sport_events.settings import Settings


def main() -> None:
    parser = argparse.ArgumentParser(description="Synchronize one Champions League season")
    parser.add_argument("season_start_year", type=int, help="Season start year, for example 2026")
    arguments = parser.parse_args()
    asyncio.run(_run(arguments.season_start_year))


async def _run(season_start_year: int) -> None:
    settings = Settings()
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    try:
        async with httpx.AsyncClient() as http_client:
            operation = SynchronizeChampionsLeagueSeason(
                source=FootballDataChampionsLeagueSource(
                    FootballDataClient(settings=settings, http_client=http_client)
                ),
                store=PostgresSeasonSnapshotStore(engine),
                lock=PostgresSeasonSyncLock(engine),
            )
            result = await operation.execute(season_start_year)
        print(
            f"Synchronized {result.matches_processed} Champions League matches "
            f"for {season_start_year}"
        )
    finally:
        await engine.dispose()


if __name__ == "__main__":
    main()
