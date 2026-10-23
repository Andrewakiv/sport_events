"""PostgreSQL journal of queued Champions League synchronization runs."""

from datetime import datetime

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncEngine

from sport_events.database.models.football import FootballSyncRun
from sport_events.football_sync.models import SyncResult
from sport_events.football_sync.runs import SyncAttempt, SyncRunStatus


class PostgresSyncRunJournal:
    """Each write is its own short transaction, independent of the season data transaction.

    Writes are upserts so that a run stays visible even when an earlier write was lost;
    ``started_at`` is set only by the first write for a run.
    """

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def start_attempt(self, attempt: SyncAttempt, started_at: datetime) -> None:
        await self._upsert(
            attempt,
            started_at,
            status=SyncRunStatus.RUNNING.value,
            finished_at=None,
            failure_reason=None,
        )

    async def record_retry(self, attempt: SyncAttempt, reason: str) -> None:
        await self._upsert(
            attempt,
            None,
            status=SyncRunStatus.RETRY_SCHEDULED.value,
            failure_reason=reason,
        )

    async def record_finished(
        self,
        attempt: SyncAttempt,
        status: SyncRunStatus,
        finished_at: datetime,
        *,
        result: SyncResult | None = None,
        reason: str | None = None,
    ) -> None:
        await self._upsert(
            attempt,
            finished_at,
            status=status.value,
            finished_at=finished_at,
            failure_reason=reason,
            matches_created=result.matches_created if result else None,
            matches_updated=result.matches_updated if result else None,
        )

    async def _upsert(
        self,
        attempt: SyncAttempt,
        first_seen_at: datetime | None,
        **changes: str | int | datetime | None,
    ) -> None:
        values = {
            "season_start_year": attempt.season_start_year,
            "trigger": attempt.trigger.value,
            "attempts": attempt.number,
            **changes,
        }
        statement = insert(FootballSyncRun).values(
            job_id=attempt.run_id,
            started_at=first_seen_at if first_seen_at is not None else func.now(),
            **values,
        )
        async with self._engine.begin() as connection:
            await connection.execute(
                statement.on_conflict_do_update(
                    index_elements=[FootballSyncRun.job_id], set_=values
                )
            )
