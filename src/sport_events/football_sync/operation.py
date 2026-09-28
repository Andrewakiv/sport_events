"""Framework-independent Champions League synchronization operation."""

from contextlib import AbstractAsyncContextManager
from typing import Protocol

from sport_events.football_sync.models import SeasonSnapshot, SyncResult


class ChampionsLeagueSource(Protocol):
    async def fetch_season(self, season_start_year: int) -> SeasonSnapshot: ...


class SeasonSnapshotStore(Protocol):
    async def store(self, snapshot: SeasonSnapshot) -> SyncResult: ...


class SeasonSyncLock(Protocol):
    def acquire(self, season_start_year: int) -> AbstractAsyncContextManager[None]: ...


class ChampionsLeagueSyncAlreadyRunningError(RuntimeError):
    """Raised when another process is already synchronizing the requested season."""


class SynchronizeChampionsLeagueSeason:
    def __init__(
        self,
        *,
        source: ChampionsLeagueSource,
        store: SeasonSnapshotStore,
        lock: SeasonSyncLock,
    ) -> None:
        self._source = source
        self._store = store
        self._lock = lock

    async def execute(self, season_start_year: int) -> SyncResult:
        """Fetch and validate before delegating one atomic persistence operation."""
        async with self._lock.acquire(season_start_year):
            snapshot = await self._source.fetch_season(season_start_year)
            return await self._store.store(snapshot)
