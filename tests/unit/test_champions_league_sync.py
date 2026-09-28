from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, date, datetime
from typing import NoReturn

import pytest

from sport_events.football_sync.models import (
    CompetitionRecord,
    MatchRecord,
    SeasonRecord,
    SeasonSnapshot,
    SyncResult,
)
from sport_events.football_sync.operation import SynchronizeChampionsLeagueSeason


def snapshot() -> SeasonSnapshot:
    return SeasonSnapshot(
        competition=CompetitionRecord(2001, "CL", "UEFA Champions League"),
        season=SeasonRecord(2557, date(2026, 9, 8), date(2027, 1, 27)),
        matches=(
            MatchRecord(
                provider_id=575341,
                kickoff_at=datetime(2026, 10, 13, 16, 45, tzinfo=UTC),
                status="TIMED",
                stage="LEAGUE_STAGE",
                matchday=2,
                group_name=None,
                home_team=None,
                away_team=None,
                home_score=None,
                away_score=None,
                score_duration="REGULAR",
            ),
        ),
    )


class RecordingLock:
    def __init__(self, calls: list[str]) -> None:
        self.calls = calls

    @asynccontextmanager
    async def acquire(self, season_start_year: int) -> AsyncIterator[None]:
        self.calls.append(f"lock:{season_start_year}")
        try:
            yield
        finally:
            self.calls.append("unlock")


class RecordingSource:
    def __init__(self, calls: list[str], value: SeasonSnapshot) -> None:
        self.calls = calls
        self.value = value

    async def fetch_season(self, season_start_year: int) -> SeasonSnapshot:
        self.calls.append(f"fetch:{season_start_year}")
        return self.value


class RecordingStore:
    def __init__(self, calls: list[str]) -> None:
        self.calls = calls

    async def store(self, value: SeasonSnapshot) -> SyncResult:
        self.calls.append("store")
        return SyncResult(matches_processed=len(value.matches))


@pytest.mark.asyncio
async def test_sync_acquires_lock_and_fetches_before_persistence() -> None:
    calls: list[str] = []
    operation = SynchronizeChampionsLeagueSeason(
        source=RecordingSource(calls, snapshot()),
        store=RecordingStore(calls),
        lock=RecordingLock(calls),
    )

    result = await operation.execute(2026)

    assert result == SyncResult(matches_processed=1)
    assert calls == ["lock:2026", "fetch:2026", "store", "unlock"]


class FailingSource:
    async def fetch_season(self, season_start_year: int) -> NoReturn:
        raise ValueError("invalid provider response")


@pytest.mark.asyncio
async def test_fetch_failure_never_calls_store_and_releases_lock() -> None:
    calls: list[str] = []
    operation = SynchronizeChampionsLeagueSeason(
        source=FailingSource(),
        store=RecordingStore(calls),
        lock=RecordingLock(calls),
    )

    with pytest.raises(ValueError, match="invalid provider response"):
        await operation.execute(2026)

    assert calls == ["lock:2026", "unlock"]
