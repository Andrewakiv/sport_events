import asyncio
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from typing import NoReturn
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

from sport_events.api.dependencies import get_database
from sport_events.database import connection as connection_module
from sport_events.database.connection import Database
from sport_events.database.football_sync import (
    PostgresSeasonSnapshotStore,
    PostgresSeasonSyncLock,
)
from sport_events.database.models.football import (
    FootballCompetition,
    FootballMatch,
    FootballSeason,
    FootballTeam,
)
from sport_events.football_models import MatchFilters
from sport_events.football_sync.models import (
    CompetitionRecord,
    MatchRecord,
    SeasonRecord,
    SeasonSnapshot,
    SyncResult,
    TeamRecord,
)
from sport_events.football_sync.operation import (
    ChampionsLeagueSyncAlreadyRunningError,
    SynchronizeChampionsLeagueSeason,
)
from sport_events.main import create_app
from sport_events.queries.champions_league_matches import ChampionsLeagueMatchQueries


@asynccontextmanager
async def migrated_engine() -> AsyncIterator[AsyncEngine]:
    database_url = os.getenv("SPORT_EVENTS_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("SPORT_EVENTS_TEST_DATABASE_URL is not configured")

    admin_engine = create_async_engine(database_url)
    schema = f"test_sync_{uuid4().hex}"
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
            yield engine
        finally:
            await engine.dispose()
    finally:
        async with admin_engine.begin() as connection:
            await connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        await admin_engine.dispose()


def season_snapshot() -> SeasonSnapshot:
    home = TeamRecord(851, "Club Brugge KV")
    away = TeamRecord(58, "Aston Villa FC")
    return SeasonSnapshot(
        competition=CompetitionRecord(2001, "CL", "UEFA Champions League"),
        season=SeasonRecord(2557, date(2026, 9, 8), date(2027, 1, 27)),
        matches=(
            MatchRecord(
                provider_id=575323,
                kickoff_at=datetime(2026, 9, 8, 16, 45, tzinfo=UTC),
                status="FINISHED",
                stage="LEAGUE_STAGE",
                matchday=1,
                group_name=None,
                home_team=home,
                away_team=away,
                home_score=2,
                away_score=3,
                score_duration="REGULAR",
            ),
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


@pytest.mark.integration
async def test_repeat_import_corrections_and_provider_omissions() -> None:
    async with migrated_engine() as engine:
        store = PostgresSeasonSnapshotStore(engine)
        original = season_snapshot()
        assert await store.store(original) == SyncResult(matches_processed=2)
        await store.store(original)

        corrected_match = replace(
            original.matches[1],
            kickoff_at=original.matches[1].kickoff_at + timedelta(hours=2),
            status="FINISHED",
            home_team=TeamRecord(546, "Racing Club de Lens"),
            away_team=TeamRecord(498, "Sporting Clube de Portugal"),
            home_score=1,
            away_score=0,
        )
        corrected = replace(original, matches=(corrected_match,))
        await store.store(corrected)

        async with engine.connect() as connection:
            assert (
                await connection.scalar(select(func.count()).select_from(FootballCompetition)) == 1
            )
            assert await connection.scalar(select(func.count()).select_from(FootballSeason)) == 1
            assert await connection.scalar(select(func.count()).select_from(FootballMatch)) == 2
            stored = (
                await connection.execute(
                    select(
                        FootballMatch.kickoff_at,
                        FootballMatch.status,
                        FootballMatch.home_score,
                        FootballMatch.away_score,
                        FootballTeam.provider_id,
                    )
                    .join(FootballTeam, FootballMatch.home_team_id == FootballTeam.id)
                    .where(FootballMatch.provider_id == corrected_match.provider_id)
                )
            ).one()
            assert stored == (
                corrected_match.kickoff_at,
                "FINISHED",
                1,
                0,
                546,
            )


@pytest.mark.integration
async def test_persistence_failure_rolls_back_whole_season() -> None:
    async with migrated_engine() as engine:
        invalid_match = replace(season_snapshot().matches[0], status="x" * 31)
        invalid = replace(season_snapshot(), matches=(season_snapshot().matches[1], invalid_match))

        with pytest.raises(DBAPIError):
            await PostgresSeasonSnapshotStore(engine).store(invalid)

        async with engine.connect() as connection:
            assert (
                await connection.scalar(select(func.count()).select_from(FootballCompetition)) == 0
            )
            assert await connection.scalar(select(func.count()).select_from(FootballSeason)) == 0
            assert await connection.scalar(select(func.count()).select_from(FootballTeam)) == 0
            assert await connection.scalar(select(func.count()).select_from(FootballMatch)) == 0


class BlockingSource:
    def __init__(self) -> None:
        self.started = asyncio.Event()
        self.release = asyncio.Event()

    async def fetch_season(self, season_start_year: int) -> SeasonSnapshot:
        self.started.set()
        await self.release.wait()
        return season_snapshot()


class UnexpectedSource:
    async def fetch_season(self, season_start_year: int) -> NoReturn:
        raise AssertionError("overlapping run must fail before fetching")


class FailingSource:
    async def fetch_season(self, season_start_year: int) -> NoReturn:
        raise RuntimeError("provider fetch failed")


class NoopStore:
    async def store(self, snapshot: SeasonSnapshot) -> SyncResult:
        return SyncResult(matches_processed=len(snapshot.matches))


@pytest.mark.integration
async def test_lock_ends_transaction_rejects_overlap_and_releases() -> None:
    async with migrated_engine() as engine:
        blocking_source = BlockingSource()
        first = SynchronizeChampionsLeagueSeason(
            source=blocking_source,
            store=NoopStore(),
            lock=PostgresSeasonSyncLock(engine),
        )
        second = SynchronizeChampionsLeagueSeason(
            source=UnexpectedSource(),
            store=NoopStore(),
            lock=PostgresSeasonSyncLock(engine),
        )

        first_task = asyncio.create_task(first.execute(2026))
        await blocking_source.started.wait()
        try:
            async with engine.connect() as observer:
                lock_rows = await observer.execute(
                    text(
                        """
                            SELECT activity.state
                            FROM pg_locks AS locks
                            JOIN pg_stat_activity AS activity ON activity.pid = locks.pid
                            WHERE locks.locktype = 'advisory'
                              AND locks.classid = :namespace
                              AND locks.objid = :season
                              AND locks.granted
                        """
                    ),
                    {"namespace": 7_200_001, "season": 2026},
                )
                lock_states = lock_rows.scalars().all()
            assert lock_states == ["idle"]

            with pytest.raises(ChampionsLeagueSyncAlreadyRunningError):
                await second.execute(2026)
        finally:
            blocking_source.release.set()
        assert await first_task == SyncResult(matches_processed=2)

        failing = SynchronizeChampionsLeagueSeason(
            source=FailingSource(),
            store=NoopStore(),
            lock=PostgresSeasonSyncLock(engine),
        )
        with pytest.raises(RuntimeError, match="provider fetch failed"):
            await failing.execute(2026)

        async with engine.connect() as observer:
            held_locks = await observer.scalar(
                text(
                    """
                    SELECT count(*)
                    FROM pg_locks
                    WHERE locktype = 'advisory'
                      AND classid = :namespace
                      AND objid = :season
                      AND granted
                    """
                ),
                {"namespace": 7_200_001, "season": 2026},
            )
        assert held_locks == 0
        assert await first.execute(2026) == SyncResult(matches_processed=2)


@pytest.mark.integration
async def test_match_reader_filters_orders_paginates_and_loads_detail() -> None:
    async with migrated_engine() as engine:
        snapshot = season_snapshot()
        await PostgresSeasonSnapshotStore(engine).store(snapshot)
        async with AsyncSession(engine) as session:
            reader = ChampionsLeagueMatchQueries(session)
            second_page = await reader.list_matches(MatchFilters(season=2026, limit=1, offset=1))
            assert second_page.total == 2
            assert second_page.items[0].id == 575341

            filtered = await reader.list_matches(
                MatchFilters(
                    season=2026,
                    date=date(2026, 9, 8),
                    team_id=851,
                    status="FINISHED",
                )
            )
            assert filtered.total == 1
            assert filtered.items[0].id == 575323
            assert filtered.items[0].stage == "LEAGUE_STAGE"
            assert filtered.items[0].score is not None
            assert filtered.items[0].score.home == 2

            assert (await reader.get_match(575323)) == filtered.items[0]
            assert await reader.get_match(999999) is None
            away_matches = await reader.list_matches(MatchFilters(team_id=58))
            assert away_matches.items == filtered.items
            scheduled = await reader.get_match(575341)
            assert scheduled is not None
            assert scheduled.home_team is None and scheduled.away_team is None
            assert scheduled.score is None
            empty_page = await reader.list_matches(MatchFilters(offset=100))
            assert empty_page.items == []
            assert empty_page.total == 2
            assert (await reader.list_matches(MatchFilters(season=2025))).total == 0
            assert (await reader.list_matches(MatchFilters(date=date.max))).total == 0

            tied_match = replace(snapshot.matches[1], kickoff_at=snapshot.matches[0].kickoff_at)
            await PostgresSeasonSnapshotStore(engine).store(
                replace(snapshot, matches=(tied_match,))
            )
            page = await reader.list_matches(MatchFilters())
            assert [match.id for match in page.items] == [575323, 575341]

            other_competition = replace(
                snapshot,
                competition=CompetitionRecord(2021, "PL", "Premier League"),
                matches=(replace(snapshot.matches[0], provider_id=999998),),
            )
            await PostgresSeasonSnapshotStore(engine).store(other_competition)
            # Drop cached ORM instances before observing imported corrections.
            session.expire_all()
            assert (await reader.list_matches(MatchFilters())).total == 2
            assert await reader.get_match(999998) is None


@pytest.mark.integration
async def test_read_api_keeps_count_and_page_on_one_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from httpx import ASGITransport, AsyncClient

    async with migrated_engine() as engine:
        store = PostgresSeasonSnapshotStore(engine)
        snapshot = season_snapshot()
        await store.store(snapshot)
        monkeypatch.setattr(connection_module, "create_async_engine", lambda *a, **kw: engine)
        database = Database("postgresql+asyncpg://unused")
        async with database.read_session() as session:
            assert await session.scalar(text("SHOW transaction_isolation")) == "read committed"
        original_execute = AsyncSession.execute
        statements = 0
        updated = False

        async def execute_then_import(
            session: AsyncSession, statement: object, **kwargs: object
        ) -> object:
            nonlocal updated, statements
            statements += 1
            result = await original_execute(session, statement, **kwargs)
            if not updated:
                updated = True
                correction = replace(
                    snapshot.matches[1], status="FINISHED", home_score=0, away_score=0
                )
                await store.store(replace(snapshot, matches=(correction,)))
            return result

        monkeypatch.setattr(AsyncSession, "execute", execute_then_import)
        app = create_app(database=database)
        app.dependency_overrides[get_database] = lambda: database
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/api/v1/football/champions-league/matches", params={"status": "TIMED"}
            )
            assert response.status_code == 200
            body = response.json()
            assert updated
            assert statements == 1
            assert body["total"] == 1
            assert len(body["items"]) == 1
            assert body["items"][0]["status"] == "TIMED"
            assert body["items"][0]["score"] is None
            assert engine.pool.checkedout() == 0

            next_response = await client.get(
                "/api/v1/football/champions-league/matches", params={"status": "TIMED"}
            )
            assert next_response.json()["total"] == 0
            assert next_response.json()["items"] == []
            assert statements == 2
            detail = await client.get("/api/v1/football/champions-league/matches/575341")
            assert detail.json()["status"] == "FINISHED"
            assert detail.json()["score"] == {"home": 0, "away": 0, "duration": "REGULAR"}
            assert engine.pool.checkedout() == 0
