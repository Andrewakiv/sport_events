"""Framework-independent rules for recording and retrying Champions League sync attempts."""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol

from sport_events.football_sync.models import SyncResult
from sport_events.football_sync.operation import ChampionsLeagueSyncAlreadyRunningError

logger = logging.getLogger(__name__)

INTERRUPTED_REASON = "worker stopped responding during the attempt"


class SyncTrigger(StrEnum):
    SCHEDULED = "scheduled"
    MANUAL = "manual"


class SyncRunStatus(StrEnum):
    RUNNING = "running"
    RETRY_SCHEDULED = "retry_scheduled"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED_LOCKED = "skipped_locked"
    INTERRUPTED = "interrupted"


class FailureKind(StrEnum):
    TRANSIENT = "transient"
    PERMANENT = "permanent"


@dataclass(frozen=True)
class SyncFailure:
    """A classified failure whose reason contains no credentials, URLs, or provider payloads."""

    kind: FailureKind
    reason: str


@dataclass(frozen=True)
class SyncRetryPolicy:
    max_attempts: int
    base_delay_seconds: int
    max_delay_seconds: int

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if not 0 < self.base_delay_seconds <= self.max_delay_seconds:
            raise ValueError("retry delays must be positive and base must not exceed max")

    def retry_delay_after(self, attempt_number: int) -> int | None:
        """Seconds to wait before the next attempt, or None when attempts are exhausted."""
        if attempt_number >= self.max_attempts:
            return None
        return min(self.base_delay_seconds * 2 ** (attempt_number - 1), self.max_delay_seconds)


@dataclass(frozen=True)
class SyncAttempt:
    """One execution of a run; ``number`` is 1 for the first attempt."""

    run_id: int
    season_start_year: int
    trigger: SyncTrigger
    number: int


class SeasonSynchronizer(Protocol):
    async def execute(self, season_start_year: int) -> SyncResult: ...


class SyncFailureClassifier(Protocol):
    def classify(self, error: Exception) -> SyncFailure: ...


class SyncRunJournal(Protocol):
    async def start_attempt(self, attempt: SyncAttempt, started_at: datetime) -> None: ...

    async def record_retry(self, attempt: SyncAttempt, reason: str) -> None: ...

    async def record_finished(
        self,
        attempt: SyncAttempt,
        status: SyncRunStatus,
        finished_at: datetime,
        *,
        result: SyncResult | None = None,
        reason: str | None = None,
    ) -> None: ...


class SyncAttemptRetryRequestedError(Exception):
    """The attempt failed transiently; the job runner should run the attempt again."""

    def __init__(self, reason: str, *, retry_in_seconds: int) -> None:
        super().__init__(reason)
        self.reason = reason
        self.retry_in_seconds = retry_in_seconds


class SyncRunFailedError(Exception):
    """The run stopped permanently; its reason is recorded in the journal."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class RunChampionsLeagueSyncAttempt:
    """Run one attempt of the season operation and record its outcome."""

    def __init__(
        self,
        *,
        synchronizer: SeasonSynchronizer,
        journal: SyncRunJournal,
        classifier: SyncFailureClassifier,
        retry_policy: SyncRetryPolicy,
        clock: Callable[[], datetime],
    ) -> None:
        self._synchronizer = synchronizer
        self._journal = journal
        self._classifier = classifier
        self._retry_policy = retry_policy
        self._clock = clock

    async def execute(self, attempt: SyncAttempt) -> SyncRunStatus:
        """Return a final status, or raise to request a retry or report a permanent failure."""
        try:
            await self._journal.start_attempt(attempt, self._clock())
            result = await self._synchronizer.execute(attempt.season_start_year)
            await self._journal.record_finished(
                attempt, SyncRunStatus.SUCCEEDED, self._clock(), result=result
            )
        except ChampionsLeagueSyncAlreadyRunningError:
            await self._journal.record_finished(
                attempt, SyncRunStatus.SKIPPED_LOCKED, self._clock()
            )
            return SyncRunStatus.SKIPPED_LOCKED
        except Exception as error:
            failure = self._classifier.classify(error)
            retry_in = (
                self._retry_policy.retry_delay_after(attempt.number)
                if failure.kind is FailureKind.TRANSIENT
                else None
            )
            await self._record_failure_best_effort(attempt, failure.reason, retry_in)
            if retry_in is not None:
                raise SyncAttemptRetryRequestedError(
                    failure.reason, retry_in_seconds=retry_in
                ) from error
            raise SyncRunFailedError(failure.reason) from error
        return SyncRunStatus.SUCCEEDED

    async def record_interruption(self, attempt: SyncAttempt) -> int | None:
        """Record an attempt abandoned by a dead worker; return the retry delay, if any."""
        retry_in = self._retry_policy.retry_delay_after(attempt.number)
        if retry_in is None:
            await self._journal.record_finished(
                attempt, SyncRunStatus.INTERRUPTED, self._clock(), reason=INTERRUPTED_REASON
            )
        else:
            await self._journal.record_retry(attempt, INTERRUPTED_REASON)
        return retry_in

    async def _record_failure_best_effort(
        self, attempt: SyncAttempt, reason: str, retry_in: int | None
    ) -> None:
        # The journal shares the database that may have caused the failure; recording must
        # not replace the classified outcome the job runner needs.
        try:
            if retry_in is None:
                await self._journal.record_finished(
                    attempt, SyncRunStatus.FAILED, self._clock(), reason=reason
                )
            else:
                await self._journal.record_retry(attempt, reason)
        except Exception:
            logger.exception("Could not record failed sync attempt %s", attempt.run_id)
