"""Football records shared by the Champions League seasons we ingest."""

from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Identity,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

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
