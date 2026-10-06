"""PostgreSQL locking and atomic persistence for football season snapshots."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from sport_events.database.models.football import (
    FootballCompetition,
    FootballMatch,
    FootballSeason,
    FootballTeam,
)
from sport_events.football_sync.models import SeasonSnapshot, SyncResult, TeamRecord
from sport_events.football_sync.operation import ChampionsLeagueSyncAlreadyRunningError

_ADVISORY_LOCK_NAMESPACE = 7_200_001


class PostgresSeasonSyncLock:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    @asynccontextmanager
    async def acquire(self, season_start_year: int) -> AsyncIterator[None]:
        async with self._engine.connect() as connection:
            acquired = await connection.scalar(
                text("SELECT pg_try_advisory_lock(:namespace, :season)"),
                {"namespace": _ADVISORY_LOCK_NAMESPACE, "season": season_start_year},
            )
            if acquired is not True:
                raise ChampionsLeagueSyncAlreadyRunningError(
                    f"Champions League season {season_start_year} is already being synchronized"
                )
            try:
                yield
            finally:
                await connection.execute(
                    text("SELECT pg_advisory_unlock(:namespace, :season)"),
                    {"namespace": _ADVISORY_LOCK_NAMESPACE, "season": season_start_year},
                )


class PostgresSeasonSnapshotStore:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def store(self, snapshot: SeasonSnapshot) -> SyncResult:
        async with self._engine.begin() as connection:
            competition_id = await self._upsert_competition(connection, snapshot)
            season_id = await self._upsert_season(connection, competition_id, snapshot)
            team_ids = await self._upsert_teams(connection, snapshot)
            await self._upsert_matches(connection, season_id, team_ids, snapshot)
        return SyncResult(matches_processed=len(snapshot.matches))

    async def _upsert_competition(
        self, connection: AsyncConnection, snapshot: SeasonSnapshot
    ) -> int:
        competition = snapshot.competition
        statement = (
            insert(FootballCompetition)
            .values(
                provider_id=competition.provider_id,
                code=competition.code,
                name=competition.name,
            )
            .on_conflict_do_update(
                index_elements=[FootballCompetition.provider_id],
                set_={"code": competition.code, "name": competition.name},
            )
            .returning(FootballCompetition.id)
        )
        competition_id = await connection.scalar(statement)
        if competition_id is None:
            raise RuntimeError("competition upsert did not return an identifier")
        return competition_id

    async def _upsert_season(
        self, connection: AsyncConnection, competition_id: int, snapshot: SeasonSnapshot
    ) -> int:
        season = snapshot.season
        statement = (
            insert(FootballSeason)
            .values(
                competition_id=competition_id,
                provider_id=season.provider_id,
                start_date=season.start_date,
                end_date=season.end_date,
            )
            .on_conflict_do_update(
                constraint="uq_football_seasons_provider",
                set_={"start_date": season.start_date, "end_date": season.end_date},
            )
            .returning(FootballSeason.id)
        )
        season_id = await connection.scalar(statement)
        if season_id is None:
            raise RuntimeError("season upsert did not return an identifier")
        return season_id

    async def _upsert_teams(
        self, connection: AsyncConnection, snapshot: SeasonSnapshot
    ) -> dict[int, int]:
        teams = {
            team.provider_id: team
            for match in snapshot.matches
            for team in (match.home_team, match.away_team)
            if team is not None
        }
        for team in teams.values():
            await self._upsert_team(connection, team)
        if not teams:
            return {}
        rows = await connection.execute(
            select(FootballTeam.provider_id, FootballTeam.id).where(
                FootballTeam.provider_id.in_(teams)
            )
        )
        return dict(rows.tuples().all())

    async def _upsert_team(self, connection: AsyncConnection, team: TeamRecord) -> None:
        await connection.execute(
            insert(FootballTeam)
            .values(provider_id=team.provider_id, name=team.name)
            .on_conflict_do_update(
                index_elements=[FootballTeam.provider_id], set_={"name": team.name}
            )
        )

    async def _upsert_matches(
        self,
        connection: AsyncConnection,
        season_id: int,
        team_ids: dict[int, int],
        snapshot: SeasonSnapshot,
    ) -> None:
        for match in snapshot.matches:
            values = {
                "provider_id": match.provider_id,
                "season_id": season_id,
                "home_team_id": (
                    team_ids[match.home_team.provider_id] if match.home_team else None
                ),
                "away_team_id": (
                    team_ids[match.away_team.provider_id] if match.away_team else None
                ),
                "kickoff_at": match.kickoff_at,
                "status": match.status,
                "stage": match.stage,
                "matchday": match.matchday,
                "group_name": match.group_name,
                "home_score": match.home_score,
                "away_score": match.away_score,
                "score_duration": match.score_duration,
            }
            await connection.execute(
                insert(FootballMatch)
                .values(**values)
                .on_conflict_do_update(
                    index_elements=[FootballMatch.provider_id],
                    set_={key: value for key, value in values.items() if key != "provider_id"},
                )
            )
