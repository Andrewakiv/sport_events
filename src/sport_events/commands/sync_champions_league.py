"""Queue a manual Champions League season synchronization for the sync worker."""

import argparse
import asyncio
import sys
from collections.abc import Callable

from procrastinate.exceptions import AlreadyEnqueued

from sport_events.football_sync.runs import SyncTrigger
from sport_events.sync_jobs.app import app
from sport_events.sync_jobs.tasks import enqueue_season_sync


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Queue one Champions League season synchronization (also used for backfill)"
    )
    parser.add_argument("season_start_year", type=int, help="Season start year, for example 2026")
    arguments = parser.parse_args()
    raise SystemExit(asyncio.run(_run(arguments.season_start_year), loop_factory=_loop_factory()))


async def _run(season_start_year: int) -> int:
    async with app.open_async():
        try:
            job_id = await enqueue_season_sync(season_start_year, SyncTrigger.MANUAL)
        except AlreadyEnqueued:
            print(f"A Champions League sync for {season_start_year} is already queued")
            return 1
    print(f"Queued Champions League sync for {season_start_year} as job {job_id}")
    return 0


def _loop_factory() -> Callable[[], asyncio.AbstractEventLoop] | None:
    # psycopg's async connections do not support the default Windows proactor loop.
    return asyncio.SelectorEventLoop if sys.platform == "win32" else None


if __name__ == "__main__":
    main()
