import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import NoReturn

import pytest

from sport_events.football_sync.models import SyncResult
from sport_events.football_sync.operation import ChampionsLeagueSyncAlreadyRunningError
from sport_events.football_sync.runs import (
    INTERRUPTED_REASON,
    SHUTDOWN_REASON,
    FailureKind,
    RunChampionsLeagueSyncAttempt,
    SyncAttempt,
    SyncAttemptRetryRequestedError,
    SyncFailure,
    SyncRetryPolicy,
    SyncRunFailedError,
    SyncRunStatus,
    SyncTrigger,
)
from sport_events.settings import Settings

NOW = datetime(2026, 10, 23, 6, 0, tzinfo=UTC)
POLICY = SyncRetryPolicy(max_attempts=3, base_delay_seconds=30, max_delay_seconds=300)


def attempt(number: int = 1) -> SyncAttempt:
    return SyncAttempt(
        run_id=41, season_start_year=2026, trigger=SyncTrigger.SCHEDULED, number=number
    )


@dataclass
class RecordingJournal:
    entries: list[tuple[object, ...]] = field(default_factory=list)
    fail_writes: bool = False

    async def start_attempt(self, attempt: SyncAttempt, started_at: datetime) -> None:
        self._write(("start", attempt.number, started_at))

    async def record_retry(self, attempt: SyncAttempt, reason: str) -> None:
        self._write(("retry", attempt.number, reason))

    async def record_finished(
        self,
        attempt: SyncAttempt,
        status: SyncRunStatus,
        finished_at: datetime,
        *,
        result: SyncResult | None = None,
        reason: str | None = None,
    ) -> None:
        self._write(("finished", status, result, reason))

    def _write(self, entry: tuple[object, ...]) -> None:
        if self.fail_writes and entry[0] != "start":
            raise ConnectionError("journal database is unavailable")
        self.entries.append(entry)


class ResultSynchronizer:
    async def execute(self, season_start_year: int) -> SyncResult:
        return SyncResult(matches_created=3, matches_updated=1)


class RaisingSynchronizer:
    def __init__(self, error: Exception) -> None:
        self.error = error

    async def execute(self, season_start_year: int) -> NoReturn:
        raise self.error


class TransientError(Exception):
    pass


class FixedClassifier:
    def classify(self, error: Exception) -> SyncFailure:
        if isinstance(error, TransientError):
            return SyncFailure(FailureKind.TRANSIENT, "provider request timed out")
        return SyncFailure(FailureKind.PERMANENT, "provider rejected the token")


def runner(
    synchronizer: ResultSynchronizer | RaisingSynchronizer, journal: RecordingJournal
) -> RunChampionsLeagueSyncAttempt:
    return RunChampionsLeagueSyncAttempt(
        synchronizer=synchronizer,
        journal=journal,
        classifier=FixedClassifier(),
        retry_policy=POLICY,
        clock=lambda: NOW,
    )


@pytest.mark.parametrize(("attempt_number", "delay"), [(1, 30), (2, 60), (3, None)])
def test_retry_policy_backs_off_until_attempts_are_exhausted(
    attempt_number: int, delay: int | None
) -> None:
    assert POLICY.retry_delay_after(attempt_number) == delay


def test_retry_policy_caps_delay() -> None:
    policy = SyncRetryPolicy(max_attempts=10, base_delay_seconds=30, max_delay_seconds=100)

    assert policy.retry_delay_after(5) == 100


@pytest.mark.parametrize(
    ("max_attempts", "base", "maximum"), [(0, 30, 300), (3, 0, 300), (3, 301, 300)]
)
def test_retry_policy_rejects_invalid_limits(max_attempts: int, base: int, maximum: int) -> None:
    with pytest.raises(ValueError):
        SyncRetryPolicy(
            max_attempts=max_attempts, base_delay_seconds=base, max_delay_seconds=maximum
        )


async def test_successful_attempt_records_counts() -> None:
    journal = RecordingJournal()

    status = await runner(ResultSynchronizer(), journal).execute(attempt())

    assert status is SyncRunStatus.SUCCEEDED
    assert journal.entries == [
        ("start", 1, NOW),
        ("finished", SyncRunStatus.SUCCEEDED, SyncResult(3, 1), None),
    ]


async def test_season_locked_by_another_run_is_skipped_without_retry() -> None:
    journal = RecordingJournal()
    synchronizer = RaisingSynchronizer(ChampionsLeagueSyncAlreadyRunningError("busy"))

    status = await runner(synchronizer, journal).execute(attempt())

    assert status is SyncRunStatus.SKIPPED_LOCKED
    assert journal.entries[-1] == ("finished", SyncRunStatus.SKIPPED_LOCKED, None, None)


async def test_transient_failure_requests_retry_with_policy_delay() -> None:
    journal = RecordingJournal()

    with pytest.raises(SyncAttemptRetryRequestedError) as raised:
        await runner(RaisingSynchronizer(TransientError()), journal).execute(attempt(2))

    assert raised.value.retry_in_seconds == 60
    assert journal.entries[-1] == ("retry", 2, "provider request timed out")


async def test_transient_failure_on_last_attempt_fails_permanently() -> None:
    journal = RecordingJournal()

    with pytest.raises(SyncRunFailedError, match="timed out"):
        await runner(RaisingSynchronizer(TransientError()), journal).execute(attempt(3))

    assert journal.entries[-1] == (
        "finished",
        SyncRunStatus.FAILED,
        None,
        "provider request timed out",
    )


async def test_permanent_failure_is_not_retried() -> None:
    journal = RecordingJournal()

    with pytest.raises(SyncRunFailedError, match="rejected the token"):
        await runner(RaisingSynchronizer(PermissionError()), journal).execute(attempt(1))

    assert journal.entries[-1] == (
        "finished",
        SyncRunStatus.FAILED,
        None,
        "provider rejected the token",
    )


async def test_journal_failure_does_not_replace_retry_decision() -> None:
    journal = RecordingJournal(fail_writes=True)

    with pytest.raises(SyncAttemptRetryRequestedError):
        await runner(RaisingSynchronizer(TransientError()), journal).execute(attempt(1))


@pytest.mark.parametrize(
    ("attempt_number", "expected_delay", "expected_entry"),
    [
        (1, 30, ("retry", 1, INTERRUPTED_REASON)),
        (3, None, ("finished", SyncRunStatus.INTERRUPTED, None, INTERRUPTED_REASON)),
    ],
)
async def test_interrupted_attempt_is_retried_while_attempts_remain(
    attempt_number: int, expected_delay: int | None, expected_entry: tuple[object, ...]
) -> None:
    journal = RecordingJournal()

    delay = await runner(ResultSynchronizer(), journal).record_interruption(attempt(attempt_number))

    assert delay == expected_delay
    assert journal.entries == [expected_entry]


async def test_locked_season_skip_survives_journal_failure() -> None:
    journal = RecordingJournal(fail_writes=True)
    synchronizer = RaisingSynchronizer(ChampionsLeagueSyncAlreadyRunningError("busy"))

    assert await runner(synchronizer, journal).execute(attempt()) is SyncRunStatus.SKIPPED_LOCKED


def test_settings_reject_retry_base_above_maximum() -> None:
    with pytest.raises(ValueError, match="base delay"):
        Settings(
            champions_league_sync_retry_base_seconds=600,
            champions_league_sync_retry_max_seconds=300,
        )


class BlockingSynchronizer:
    def __init__(self) -> None:
        self.started = asyncio.Event()

    async def execute(self, season_start_year: int) -> NoReturn:
        self.started.set()
        await asyncio.Event().wait()
        raise AssertionError("unreachable")


@pytest.mark.parametrize(
    ("attempt_number", "expected_entry"),
    [
        (1, ("retry", 1, SHUTDOWN_REASON)),
        (3, ("finished", SyncRunStatus.INTERRUPTED, None, SHUTDOWN_REASON)),
    ],
)
async def test_cancelled_attempt_is_journaled_and_cancellation_propagates(
    attempt_number: int, expected_entry: tuple[object, ...]
) -> None:
    journal = RecordingJournal()
    synchronizer = BlockingSynchronizer()
    running = asyncio.create_task(runner(synchronizer, journal).execute(attempt(attempt_number)))
    await synchronizer.started.wait()

    running.cancel()
    with pytest.raises(asyncio.CancelledError):
        await running

    assert journal.entries[-1] == expected_entry
