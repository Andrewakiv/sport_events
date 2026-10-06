"""Plain records used by the football read API."""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol


@dataclass(frozen=True)
class TeamView:
    provider_id: int
    name: str


@dataclass(frozen=True)
class SeasonView:
    provider_id: int
    start_date: date
    end_date: date


@dataclass(frozen=True)
class MatchView:
    provider_id: int
    season: SeasonView
    kickoff_at: datetime
    status: str
    stage: str
    matchday: int | None
    group_name: str | None
    home_team: TeamView | None
    away_team: TeamView | None
    home_score: int | None
    away_score: int | None
    score_duration: str | None


@dataclass(frozen=True)
class MatchListQuery:
    season_start_year: int | None = None
    match_date: date | None = None
    team_provider_id: int | None = None
    status: str | None = None
    limit: int = 50
    offset: int = 0


@dataclass(frozen=True)
class MatchPage:
    items: tuple[MatchView, ...]
    total: int
    limit: int
    offset: int


class FootballMatchReader(Protocol):
    async def list_matches(self, query: MatchListQuery) -> MatchPage: ...

    async def get_match(self, provider_id: int) -> MatchView | None: ...
