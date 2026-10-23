import asyncio
import os
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from procrastinate import PsycopgConnector
from procrastinate.exceptions import AlreadyEnqueued
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from sport_events.database.football_sync_runs import PostgresSyncRunJournal
from sport_events.database.models.football import FootballSyncRun
from sport_events.football_sync.models import SyncResult
from sport_events.football_sync.runs import (
    INTERRUPTED_REASON,
    RunChampionsLeagueSyncAttempt,
    SyncAttempt,
    SyncRetryPolicy,
    SyncRunStatus,
    SyncTrigger,
)
from sport_events.settings import Settings
from sport_events.sync_jobs import tasks
from sport_events.sync_jobs.app import app, queue_conninfo
from sport_events.sync_jobs.failures import ChampionsLeagueSyncFailureClassifier

T0 = datetime(2026, 10, 23, 6, 0, tzinfo=UTC)


@pytest.fixture(scope="module")
def event_loop_policy() -> asyncio.AbstractEventLoopPolicy:
    # psycopg's async connections need a selector loop on Windows.
    if sys.platform == "win32":
        return asyncio.WindowsSelectorEventLoopPolicy()
    return asyncio.DefaultEventLoopPolicy()


@asynccontextmanager
async def migrated_schema() -> AsyncIterator[tuple[str, str, AsyncEngine]]:
    database_url = os.getenv("SPORT_EVENTS_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("SPORT_EVENTS_TEST_DATABASE_URL is not configured")

    admin_engine = create_async_engine(database_url)
    schema = f"test_jobs_{uuid4().hex}"
    config = Config("alembic.ini")
    try:
        async with admin_engine.begin() as connection:
            await connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        engine = create_async_engine(
            database_url, connect_args={"server_settings": {"search_path": schema}}
        )
        try:
            async with engine.begin() as connection:

                def migrate(sync_connection: object) -> None:
                    config.attributes["connection"] = sync_connection
                    command.upgrade(config, "head")

                await connection.run_sync(migrate)
            yield database_url, schema, engine
        finally:
            await engine.dispose()
    finally:
        async with admin_engine.begin() as connection:
            await connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        await admin_engine.dispose()


async def procrastinate_objects(engine: AsyncEngine) -> set[str]:
    async with engine.connect() as connection:
        rows = await connection.execute(
            text(
                """
                SELECT c.relname FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = current_schema() AND c.relname LIKE 'procrastinate%'
                UNION ALL
                SELECT p.proname FROM pg_proc p
                JOIN pg_namespace n ON n.oid = p.pronamespace
                WHERE n.nspname = current_schema() AND p.proname LIKE 'procrastinate%'
                UNION ALL
                SELECT t.typname FROM pg_type t
                JOIN pg_namespace n ON n.oid = t.typnamespace
                WHERE n.nspname = current_schema() AND t.typname LIKE 'procrastinate%'
                """
            )
        )
        return set(rows.scalars().all())


@pytest.mark.integration
async def test_queue_schema_migration_round_trip() -> None:
    async with migrated_schema() as (_, _, engine):
        installed = await procrastinate_objects(engine)
        assert {"procrastinate_jobs", "procrastinate_workers", "procrastinate_fetch_job_v2"} <= (
            installed
        )

        async with engine.begin() as connection:

            def migrate(sync_connection: object, revision: str, upgrade: bool) -> None:
                config = Config("alembic.ini")
                config.attributes["connection"] = sync_connection
                if upgrade:
                    command.upgrade(config, revision)
                else:
                    command.downgrade(config, revision)

            await connection.run_sync(migrate, "0002_football_schema", False)
        assert await procrastinate_objects(engine) == set()

        async with engine.begin() as connection:
            await connection.run_sync(migrate, "head", True)
        assert await procrastinate_objects(engine) == installed


async def stored_run(engine: AsyncEngine, job_id: int) -> FootballSyncRun:
    async with engine.connect() as connection:
        row = (
            await connection.execute(
                select(FootballSyncRun).where(FootballSyncRun.job_id == job_id)
            )
        ).one()
    return FootballSyncRun(**row._asdict())


@pytest.mark.integration
async def test_journal_keeps_first_start_and_final_outcome() -> None:
    async with migrated_schema() as (_, _, engine):
        journal = PostgresSyncRunJournal(engine)
        first = SyncAttempt(11, 2026, SyncTrigger.SCHEDULED, 1)
        second = SyncAttempt(11, 2026, SyncTrigger.SCHEDULED, 2)

        await journal.start_attempt(first, T0)
        await journal.record_retry(first, "provider request timed out")
        run = await stored_run(engine, 11)
        assert (run.status, run.attempts, run.failure_reason) == (
            "retry_scheduled",
            1,
            "provider request timed out",
        )

        await journal.start_attempt(second, T0 + timedelta(minutes=1))
        await journal.record_finished(
            second,
            SyncRunStatus.SUCCEEDED,
            T0 + timedelta(minutes=2),
            result=SyncResult(matches_created=2, matches_updated=5),
        )
        run = await stored_run(engine, 11)
        assert (
            run.status,
            run.attempts,
            run.started_at,
            run.finished_at,
            run.matches_created,
            run.matches_updated,
            run.failure_reason,
        ) == ("succeeded", 2, T0, T0 + timedelta(minutes=2), 2, 5, None)

        orphan = SyncAttempt(12, 2025, SyncTrigger.MANUAL, 3)
        await journal.record_finished(
            orphan, SyncRunStatus.INTERRUPTED, T0, reason=INTERRUPTED_REASON
        )
        run = await stored_run(engine, 12)
        assert (run.status, run.trigger, run.started_at) == ("interrupted", "manual", T0)


class CountingSynchronizer:
    def __init__(self) -> None:
        self.seasons: list[int] = []

    async def execute(self, season_start_year: int) -> SyncResult:
        self.seasons.append(season_start_year)
        return SyncResult(matches_created=1, matches_updated=0)


@pytest.mark.integration
async def test_queue_rejects_overlap_and_recovers_interrupted_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async with migrated_schema() as (database_url, schema, engine):
        synchronizer = CountingSynchronizer()

        @asynccontextmanager
        async def test_runner(settings: Settings) -> AsyncIterator[RunChampionsLeagueSyncAttempt]:
            yield RunChampionsLeagueSyncAttempt(
                synchronizer=synchronizer,
                journal=PostgresSyncRunJournal(engine),
                classifier=ChampionsLeagueSyncFailureClassifier(),
                retry_policy=SyncRetryPolicy(
                    max_attempts=3, base_delay_seconds=30, max_delay_seconds=300
                ),
                clock=lambda: datetime.now(UTC),
            )

        monkeypatch.setattr(tasks, "sync_attempt_runner", test_runner)
        monkeypatch.setattr(tasks, "get_settings", lambda: Settings())
        connector = PsycopgConnector(
            conninfo=queue_conninfo(database_url),
            kwargs={"options": f"-c search_path={schema}"},
        )
        with app.replace_connector(connector):
            async with app.open_async():
                job_id = await tasks.enqueue_season_sync(2026, SyncTrigger.SCHEDULED)
                with pytest.raises(AlreadyEnqueued):
                    await tasks.enqueue_season_sync(2026, SyncTrigger.MANUAL)

                # A worker that died mid-attempt leaves its job "doing" without a live worker.
                async with engine.begin() as connection:
                    await connection.execute(
                        text("UPDATE procrastinate_jobs SET status = 'doing' WHERE id = :id"),
                        {"id": job_id},
                    )

                context = SimpleNamespace(app=app)
                assert await tasks.recover_stalled_syncs(context, timestamp=0) == 1
                run = await stored_run(engine, job_id)
                assert (run.status, run.failure_reason) == ("retry_scheduled", INTERRUPTED_REASON)

                async with engine.begin() as connection:
                    status, attempts = (
                        await connection.execute(
                            text(
                                "SELECT status::text, attempts FROM procrastinate_jobs "
                                "WHERE id = :id"
                            ),
                            {"id": job_id},
                        )
                    ).one()
                    assert (status, attempts) == ("todo", 1)
                    await connection.execute(
                        text("UPDATE procrastinate_jobs SET scheduled_at = now() WHERE id = :id"),
                        {"id": job_id},
                    )

                await app.run_worker_async(
                    queues=[tasks.QUEUE],
                    wait=False,
                    install_signal_handlers=False,
                    listen_notify=False,
                )

        assert synchronizer.seasons == [2026]
        run = await stored_run(engine, job_id)
        assert (run.status, run.attempts, run.matches_created, run.failure_reason) == (
            "succeeded",
            2,
            1,
            None,
        )
