"""Queued, scheduled, and recovery jobs for Champions League synchronization."""

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta

import httpx
from procrastinate import BaseRetryStrategy, JobContext, RetryDecision
from procrastinate.exceptions import AlreadyEnqueued
from procrastinate.jobs import Job, Status
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from sport_events.database.football_sync import (
    PostgresSeasonSnapshotStore,
    PostgresSeasonSyncLock,
)
from sport_events.database.football_sync_runs import PostgresSyncRunJournal
from sport_events.football_data.client import FootballDataClient
from sport_events.football_data.sync_source import FootballDataChampionsLeagueSource
from sport_events.football_sync.models import SyncResult
from sport_events.football_sync.operation import SynchronizeChampionsLeagueSeason
from sport_events.football_sync.runs import (
    RunChampionsLeagueSyncAttempt,
    SyncAttempt,
    SyncAttemptRetryRequestedError,
    SyncRetryPolicy,
    SyncTrigger,
)
from sport_events.settings import Settings, get_settings
from sport_events.sync_jobs.app import app
from sport_events.sync_jobs.failures import ChampionsLeagueSyncFailureClassifier

logger = logging.getLogger(__name__)

QUEUE = "football"
SYNC_SEASON_TASK = "sync_champions_league_season"
FINISHED_JOB_RETENTION_HOURS = 14 * 24


class RetryRequestedBySyncAttempt(BaseRetryStrategy):
    """Retry when the sync rules ask for it, or when shutdown cancelled an attempt.

    Procrastinate cancels async jobs that outlive ``--shutdown-graceful-timeout``; the run
    rules have already journaled the interruption, and the same policy bounds its retries.
    """

    def get_retry_decision(self, *, exception: BaseException, job: Job) -> RetryDecision | None:
        if isinstance(exception, SyncAttemptRetryRequestedError):
            return RetryDecision(retry_in={"seconds": exception.retry_in_seconds})
        if isinstance(exception, asyncio.CancelledError):
            # Only graceful-shutdown cancellation is expected today; if job aborting is ever
            # used, distinguish it here so aborted jobs are not retried.
            retry_in = retry_policy(get_settings()).retry_delay_after(job.attempts + 1)
            if retry_in is not None:
                return RetryDecision(retry_in={"seconds": retry_in})
        return None


def season_lock(season_start_year: int) -> str:
    return f"champions-league-season-{season_start_year}"


async def enqueue_season_sync(season_start_year: int, trigger: SyncTrigger) -> int:
    """Queue one run and return its job id.

    Raises ``AlreadyEnqueued`` while another run for the season is waiting; the same lock
    keeps two runs for one season from executing at the same time.
    """
    lock = season_lock(season_start_year)
    return await sync_champions_league_season.configure(lock=lock, queueing_lock=lock).defer_async(
        season_start_year=season_start_year, trigger=trigger.value
    )


@app.task(
    name=SYNC_SEASON_TASK,
    queue=QUEUE,
    pass_context=True,
    retry=RetryRequestedBySyncAttempt(),
)
async def sync_champions_league_season(
    context: JobContext, season_start_year: int, trigger: str
) -> str:
    # The arguments only identify the run; the attempt is rebuilt from the job so that
    # retries use the queue's attempt counter, not the values passed at enqueue time.
    async with sync_attempt_runner(get_settings()) as runner:
        status = await runner.execute(attempt_from_job(context.job))
    return status.value


@app.periodic(
    cron=get_settings().champions_league_sync_cron,
    periodic_id="champions-league-current-season",
)
@app.task(name="schedule_champions_league_sync", queue=QUEUE)
async def schedule_current_season_sync(timestamp: int) -> None:
    season = get_settings().champions_league_sync_season
    if season is None:
        logger.info("No current Champions League season is configured; nothing to schedule")
        return
    try:
        await enqueue_season_sync(season, SyncTrigger.SCHEDULED)
    except AlreadyEnqueued:
        logger.info("Champions League season %s is already queued", season)


@app.periodic(cron="*/5 * * * *", periodic_id="recover-stalled-champions-league-syncs")
@app.task(name="recover_stalled_champions_league_syncs", queue=QUEUE, pass_context=True)
async def recover_stalled_syncs(context: JobContext, timestamp: int) -> int:
    """Record attempts left running by a dead worker, then retry or fail their jobs."""
    settings = get_settings()
    manager = context.app.job_manager
    stalled = list(
        await manager.get_stalled_jobs(
            task_name=SYNC_SEASON_TASK,
            seconds_since_heartbeat=settings.sync_worker_stalled_after_seconds,
        )
    )
    if not stalled:
        return 0
    async with sync_attempt_runner(settings) as runner:
        for job in stalled:
            # The journal and the queue are updated separately. If this worker dies in
            # between, the job is still "doing" and the next pass repeats both upserts.
            retry_in = await runner.record_interruption(attempt_from_job(job))
            if retry_in is None:
                await manager.finish_job(job, status=Status.FAILED, delete_job=False)
            else:
                await manager.retry_job(
                    job, retry_at=datetime.now(UTC) + timedelta(seconds=retry_in)
                )
    return len(stalled)


@app.periodic(cron="30 3 * * *", periodic_id="remove-old-sync-jobs")
@app.task(name="remove_old_sync_jobs", queue=QUEUE, pass_context=True)
async def remove_old_sync_jobs(context: JobContext, timestamp: int) -> None:
    """Keep the queue small; football_sync_runs is the durable record of each run."""
    await context.app.job_manager.delete_old_jobs(
        nb_hours=FINISHED_JOB_RETENTION_HOURS, queue=QUEUE, include_failed=True
    )


def attempt_from_job(job: Job) -> SyncAttempt:
    season_start_year = job.task_kwargs.get("season_start_year")
    trigger = job.task_kwargs.get("trigger")
    if job.id is None or not isinstance(season_start_year, int) or not isinstance(trigger, str):
        raise RuntimeError(f"job {job.id} has unexpected sync arguments")
    return SyncAttempt(
        run_id=job.id,
        season_start_year=season_start_year,
        trigger=SyncTrigger(trigger),
        number=job.attempts + 1,
    )


def retry_policy(settings: Settings) -> SyncRetryPolicy:
    return SyncRetryPolicy(
        max_attempts=settings.champions_league_sync_max_attempts,
        base_delay_seconds=settings.champions_league_sync_retry_base_seconds,
        max_delay_seconds=settings.champions_league_sync_retry_max_seconds,
    )


class ConfiguredSeasonSynchronizer:
    """Build the provider client inside the attempt so configuration errors are journaled."""

    def __init__(
        self, *, settings: Settings, engine: AsyncEngine, http_client: httpx.AsyncClient
    ) -> None:
        self._settings = settings
        self._engine = engine
        self._http_client = http_client

    async def execute(self, season_start_year: int) -> SyncResult:
        operation = SynchronizeChampionsLeagueSeason(
            source=FootballDataChampionsLeagueSource(
                FootballDataClient(settings=self._settings, http_client=self._http_client)
            ),
            store=PostgresSeasonSnapshotStore(self._engine),
            lock=PostgresSeasonSyncLock(self._engine),
        )
        return await operation.execute(season_start_year)


@asynccontextmanager
async def sync_attempt_runner(settings: Settings) -> AsyncIterator[RunChampionsLeagueSyncAttempt]:
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    try:
        async with httpx.AsyncClient() as http_client:
            yield RunChampionsLeagueSyncAttempt(
                synchronizer=ConfiguredSeasonSynchronizer(
                    settings=settings, engine=engine, http_client=http_client
                ),
                journal=PostgresSyncRunJournal(engine),
                classifier=ChampionsLeagueSyncFailureClassifier(),
                retry_policy=retry_policy(settings),
                clock=lambda: datetime.now(UTC),
            )
    finally:
        await engine.dispose()
