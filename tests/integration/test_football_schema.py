import os
from datetime import UTC, date, datetime
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import insert, inspect, select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine

from sport_events.database.models.football import (
    FootballCompetition,
    FootballMatch,
    FootballSeason,
    FootballTeam,
)


@pytest.mark.integration
async def test_football_migration_and_match_constraints() -> None:
    database_url = os.getenv("SPORT_EVENTS_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("SPORT_EVENTS_TEST_DATABASE_URL is not configured")

    engine = create_async_engine(database_url)
    schema = f"test_football_{uuid4().hex}"
    config = Config("alembic.ini")

    try:
        async with engine.begin() as connection:
            await connection.execute(text(f'CREATE SCHEMA "{schema}"'))

        async with engine.begin() as connection:
            await connection.execute(text(f'SET LOCAL search_path TO "{schema}"'))

            def migrate(sync_connection: object, revision: str) -> None:
                config.attributes["connection"] = sync_connection
                command.upgrade(config, revision)

            await connection.run_sync(migrate, "head")
            tables = await connection.run_sync(lambda sync: inspect(sync).get_table_names())
            assert set(tables) >= {
                "football_competitions",
                "football_seasons",
                "football_teams",
                "football_matches",
            }

            competition_id = await connection.scalar(
                insert(FootballCompetition)
                .values(provider_id=2001, code="CL", name="UEFA Champions League")
                .returning(FootballCompetition.id)
            )
            season_id = await connection.scalar(
                insert(FootballSeason)
                .values(
                    competition_id=competition_id,
                    provider_id=2557,
                    start_date=date(2026, 9, 8),
                    end_date=date(2027, 1, 27),
                )
                .returning(FootballSeason.id)
            )
            scheduled_match = dict(
                provider_id=575341,
                season_id=season_id,
                home_team_id=None,
                away_team_id=None,
                kickoff_at=datetime(2026, 10, 13, 16, 45, tzinfo=UTC),
                status="TIMED",
                stage="LEAGUE_STAGE",
                matchday=2,
                group_name=None,
                home_score=None,
                away_score=None,
                score_duration=None,
            )
            match_id = await connection.scalar(
                insert(FootballMatch).values(**scheduled_match).returning(FootballMatch.id)
            )
            stored_match = (
                await connection.execute(
                    select(
                        FootballMatch.home_team_id,
                        FootballMatch.away_team_id,
                        FootballMatch.home_score,
                    ).where(FootballMatch.id == match_id)
                )
            ).one()
            assert stored_match.home_team_id is None
            assert stored_match.away_team_id is None
            assert stored_match.home_score is None

            home_team_id = await connection.scalar(
                insert(FootballTeam)
                .values(provider_id=546, name="Racing Club de Lens")
                .returning(FootballTeam.id)
            )
            away_team_id = await connection.scalar(
                insert(FootballTeam)
                .values(provider_id=498, name="Sporting Clube de Portugal")
                .returning(FootballTeam.id)
            )
            await connection.execute(
                update(FootballMatch)
                .where(FootballMatch.id == match_id)
                .values(
                    home_team_id=home_team_id,
                    away_team_id=away_team_id,
                    status="FINISHED",
                    home_score=2,
                    away_score=1,
                    score_duration="REGULAR",
                )
            )
            scores = (
                await connection.execute(
                    select(FootballMatch.home_score, FootballMatch.away_score).where(
                        FootballMatch.id == match_id
                    )
                )
            ).one()
            assert scores == (2, 1)

            with pytest.raises(IntegrityError):
                async with connection.begin_nested():
                    await connection.execute(insert(FootballMatch).values(**scheduled_match))

            with pytest.raises(IntegrityError):
                async with connection.begin_nested():
                    await connection.execute(
                        insert(FootballMatch).values(
                            **{**scheduled_match, "provider_id": 575342, "home_score": 1}
                        )
                    )

            with pytest.raises(IntegrityError):
                async with connection.begin_nested():
                    await connection.execute(
                        insert(FootballMatch).values(
                            **{**scheduled_match, "provider_id": 575343, "season_id": -1}
                        )
                    )

        async with engine.begin() as connection:
            await connection.execute(text(f'SET LOCAL search_path TO "{schema}"'))

            def downgrade(sync_connection: object) -> None:
                config.attributes["connection"] = sync_connection
                command.downgrade(config, "0001_baseline")

            await connection.run_sync(downgrade)
            tables = await connection.run_sync(lambda sync: inspect(sync).get_table_names())
            assert "football_matches" not in tables
    finally:
        async with engine.begin() as connection:
            await connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        await engine.dispose()
