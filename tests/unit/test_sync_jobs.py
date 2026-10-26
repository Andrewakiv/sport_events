import asyncio
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any

import pytest
from procrastinate import App
from procrastinate.exceptions import AlreadyEnqueued
from procrastinate.jobs import Job
from procrastinate.testing import InMemoryConnector

from sport_events.commands import sync_champions_league
from sport_events.football_sync.runs import (
    SyncAttempt,
    SyncAttemptRetryRequestedError,
    SyncRunFailedError,
    SyncRunStatus,
    SyncTrigger,
)
from sport_events.settings import Settings
from sport_events.sync_jobs import tasks
from sport_events.sync_jobs.app import app, queue_conninfo


@pytest.fixture
def connector() -> Iterator[InMemoryConnector]:
    in_memory = InMemoryConnector()
    with app.replace_connector(in_memory):
        yield in_memory


class FakeRunner:
    def __init__(self, interruption_delay: int | None = None) -> None:
        self.executed: list[SyncAttempt] = []
        self.interrupted: list[SyncAttempt] = []
        self.interruption_delay = interruption_delay

    async def execute(self, attempt: SyncAttempt) -> SyncRunStatus:
        self.executed.append(attempt)
        return SyncRunStatus.SUCCEEDED

    async def record_interruption(self, attempt: SyncAttempt) -> int | None:
        self.interrupted.append(attempt)
        return self.interruption_delay


def use_runner(monkeypatch: pytest.MonkeyPatch, runner: FakeRunner) -> None:
    @asynccontextmanager
    async def fake_runner(settings: Settings) -> AsyncIterator[FakeRunner]:
        yield runner

    monkeypatch.setattr(tasks, "sync_attempt_runner", fake_runner)


def use_settings(monkeypatch: pytest.MonkeyPatch, **values: Any) -> None:
    monkeypatch.setattr(tasks, "get_settings", lambda: Settings(**values))


def job(**changes: Any) -> Job:
    values: dict[str, Any] = {
        "id": 7,
        "queue": tasks.QUEUE,
        "lock": None,
        "queueing_lock": None,
        "task_name": tasks.SYNC_SEASON_TASK,
        "task_kwargs": {"season_start_year": 2026, "trigger": "scheduled"},
        "attempts": 0,
    }
    return Job(**(values | changes))


def test_queue_conninfo_uses_libpq_scheme() -> None:
    assert (
        queue_conninfo("postgresql+asyncpg://user:secret@db:5432/sport_events")
        == "postgresql://user:secret@db:5432/sport_events"
    )


async def test_one_waiting_run_per_season(connector: InMemoryConnector) -> None:
    first = await tasks.enqueue_season_sync(2026, SyncTrigger.MANUAL)
    with pytest.raises(AlreadyEnqueued):
        await tasks.enqueue_season_sync(2026, SyncTrigger.SCHEDULED)
    await tasks.enqueue_season_sync(2025, SyncTrigger.MANUAL)

    row = connector.jobs[first]
    assert row["lock"] == row["queueing_lock"] == "champions-league-season-2026"
    assert row["args"] == {"season_start_year": 2026, "trigger": "manual"}
    assert len(connector.jobs) == 2


async def test_schedule_without_configured_season_queues_nothing(
    connector: InMemoryConnector, monkeypatch: pytest.MonkeyPatch
) -> None:
    use_settings(monkeypatch, champions_league_sync_season=None)

    await tasks.schedule_current_season_sync(timestamp=0)

    assert connector.jobs == {}


async def test_schedule_queues_only_the_configured_current_season(
    connector: InMemoryConnector, monkeypatch: pytest.MonkeyPatch
) -> None:
    use_settings(monkeypatch, champions_league_sync_season=2026)

    await tasks.schedule_current_season_sync(timestamp=0)
    await tasks.schedule_current_season_sync(timestamp=1)

    assert [row["args"] for row in connector.jobs.values()] == [
        {"season_start_year": 2026, "trigger": "scheduled"}
    ]


async def test_sync_task_runs_attempt_numbered_from_job_attempts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = FakeRunner()
    use_runner(monkeypatch, runner)
    context = SimpleNamespace(job=job(attempts=1))

    status = await tasks.sync_champions_league_season(
        context, season_start_year=2026, trigger="scheduled"
    )

    assert status == "succeeded"
    assert runner.executed == [SyncAttempt(7, 2026, SyncTrigger.SCHEDULED, 2)]


def test_retry_strategy_follows_sync_decision() -> None:
    strategy = tasks.RetryRequestedBySyncAttempt()
    requested = SyncAttemptRetryRequestedError("timed out", retry_in_seconds=60)

    decision = strategy.get_retry_decision(exception=requested, job=job())

    assert decision is not None
    assert decision.retry_at is not None
    expected = datetime.now(UTC) + timedelta(seconds=60)
    assert abs((decision.retry_at - expected).total_seconds()) < 5
    for error in (SyncRunFailedError("rejected"), TimeoutError()):
        assert strategy.get_retry_decision(exception=error, job=job()) is None


@pytest.mark.parametrize(("attempts", "retried"), [(0, True), (1, True), (2, False)])
def test_retry_strategy_retries_shutdown_cancellation_within_attempts(
    monkeypatch: pytest.MonkeyPatch, attempts: int, retried: bool
) -> None:
    use_settings(monkeypatch, champions_league_sync_max_attempts=3)

    decision = tasks.RetryRequestedBySyncAttempt().get_retry_decision(
        exception=asyncio.CancelledError(), job=job(attempts=attempts)
    )

    assert (decision is not None) is retried


@pytest.mark.parametrize(
    ("delay", "expected_status", "expected_attempts"),
    [(30, "todo", 1), (None, "failed", 1)],
)
async def test_recovery_retries_or_fails_stalled_runs(
    connector: InMemoryConnector,
    monkeypatch: pytest.MonkeyPatch,
    delay: int | None,
    expected_status: str,
    expected_attempts: int,
) -> None:
    use_settings(monkeypatch)
    runner = FakeRunner(interruption_delay=delay)
    use_runner(monkeypatch, runner)
    job_id = await tasks.enqueue_season_sync(2026, SyncTrigger.SCHEDULED)
    connector.jobs[job_id]["status"] = "doing"

    recovered = await tasks.recover_stalled_syncs(SimpleNamespace(app=app), timestamp=0)

    assert recovered == 1
    assert runner.interrupted == [SyncAttempt(job_id, 2026, SyncTrigger.SCHEDULED, 1)]
    assert connector.jobs[job_id]["status"] == expected_status
    assert connector.jobs[job_id]["attempts"] == expected_attempts


async def test_recovery_without_stalled_runs_opens_nothing(
    connector: InMemoryConnector, monkeypatch: pytest.MonkeyPatch
) -> None:
    use_settings(monkeypatch)

    @asynccontextmanager
    async def unexpected_runner(settings: Settings) -> AsyncIterator[None]:
        raise AssertionError("no runner is needed without stalled jobs")
        yield

    monkeypatch.setattr(tasks, "sync_attempt_runner", unexpected_runner)
    await tasks.enqueue_season_sync(2026, SyncTrigger.SCHEDULED)

    assert await tasks.recover_stalled_syncs(SimpleNamespace(app=app), timestamp=0) == 0


def test_attempt_from_job_rejects_unexpected_arguments() -> None:
    with pytest.raises(RuntimeError, match="unexpected sync arguments"):
        tasks.attempt_from_job(job(task_kwargs={"season_start_year": "2026"}))


async def test_command_reports_already_queued_season(connector: InMemoryConnector) -> None:
    assert await sync_champions_league._run(2026) == 0
    assert await sync_champions_league._run(2026) == 1


def test_periodic_jobs_are_registered() -> None:
    assert isinstance(app, App)
    periodic_ids = {task.periodic_id for task in app.periodic_registry.periodic_tasks.values()}
    assert periodic_ids == {
        "champions-league-current-season",
        "recover-stalled-champions-league-syncs",
        "remove-old-sync-jobs",
    }
