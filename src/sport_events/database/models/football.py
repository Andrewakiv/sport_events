"""Football records shared by the Champions League seasons we ingest."""

from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sport_events.database.base import DatabaseModel


class FootballCompetition(DatabaseModel):
    __tablename__ = "football_competitions"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    provider_id: Mapped[int] = mapped_column(unique=True)
    code: Mapped[str] = mapped_column(String(20))
    name: Mapped[str] = mapped_column(String(150))


class FootballSeason(DatabaseModel):
    __tablename__ = "football_seasons"
    __table_args__ = (
        UniqueConstraint("competition_id", "provider_id", name="uq_football_seasons_provider"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    competition_id: Mapped[int] = mapped_column(ForeignKey("football_competitions.id"))
    provider_id: Mapped[int]
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    competition: Mapped[FootballCompetition] = relationship()


class FootballTeam(DatabaseModel):
    __tablename__ = "football_teams"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    provider_id: Mapped[int] = mapped_column(unique=True)
    name: Mapped[str] = mapped_column(String(150))


class FootballMatch(DatabaseModel):
    __tablename__ = "football_matches"
    __table_args__ = (
        CheckConstraint(
            "(home_score IS NULL AND away_score IS NULL) "
            "OR (home_score IS NOT NULL AND away_score IS NOT NULL)",
            name="ck_football_matches_complete_score",
        ),
        CheckConstraint(
            "home_score >= 0 AND away_score >= 0",
            name="ck_football_matches_score_nonnegative",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    provider_id: Mapped[int] = mapped_column(unique=True)
    season_id: Mapped[int] = mapped_column(ForeignKey("football_seasons.id"))
    home_team_id: Mapped[int | None] = mapped_column(ForeignKey("football_teams.id"))
    away_team_id: Mapped[int | None] = mapped_column(ForeignKey("football_teams.id"))
    kickoff_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(30))
    stage: Mapped[str] = mapped_column(String(40))
    matchday: Mapped[int | None]
    group_name: Mapped[str | None] = mapped_column(String(50))
    home_score: Mapped[int | None]
    away_score: Mapped[int | None]
    score_duration: Mapped[str | None] = mapped_column(String(30))
    season: Mapped[FootballSeason] = relationship()
    home_team: Mapped[FootballTeam | None] = relationship(foreign_keys=[home_team_id])
    away_team: Mapped[FootballTeam | None] = relationship(foreign_keys=[away_team_id])


class FootballSyncRun(DatabaseModel):
    """Durable outcome of one queued season synchronization; job_id is the queue's job."""

    __tablename__ = "football_sync_runs"
    __table_args__ = (
        CheckConstraint("trigger IN ('scheduled', 'manual')", name="ck_football_sync_runs_trigger"),
        CheckConstraint(
            "status IN ('running', 'retry_scheduled', 'succeeded', 'failed', "
            "'skipped_locked', 'interrupted')",
            name="ck_football_sync_runs_status",
        ),
        CheckConstraint("attempts >= 1", name="ck_football_sync_runs_attempts"),
        CheckConstraint(
            "matches_created >= 0 AND matches_updated >= 0",
            name="ck_football_sync_runs_counts_nonnegative",
        ),
        Index("ix_football_sync_runs_season_started", "season_start_year", "started_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    job_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    season_start_year: Mapped[int]
    trigger: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20))
    attempts: Mapped[int]
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    matches_created: Mapped[int | None]
    matches_updated: Mapped[int | None]
    failure_reason: Mapped[str | None] = mapped_column(String(200))
