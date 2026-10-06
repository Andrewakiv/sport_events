"""Map football-data.org responses to provider-neutral synchronization records."""

from typing import Protocol

from sport_events.football_data.errors import FootballDataResponseError
from sport_events.football_data.schemas import FootballDataMatch, FootballDataTeam
from sport_events.football_sync.models import (
    CompetitionRecord,
    MatchRecord,
    SeasonRecord,
    SeasonSnapshot,
    TeamRecord,
)

CHAMPIONS_LEAGUE_NAME = "UEFA Champions League"


class FootballDataMatchClient(Protocol):
    async def get_champions_league_matches(
        self, season_start_year: int
    ) -> tuple[FootballDataMatch, ...]: ...


class FootballDataChampionsLeagueSource:
    def __init__(self, client: FootballDataMatchClient) -> None:
        self._client = client

    async def fetch_season(self, season_start_year: int) -> SeasonSnapshot:
        matches = await self._client.get_champions_league_matches(season_start_year)
        try:
            return _to_snapshot(matches, season_start_year)
        except ValueError as exc:
            raise FootballDataResponseError(
                "football-data.org returned an inconsistent season response"
            ) from exc


def _to_snapshot(matches: tuple[FootballDataMatch, ...], season_start_year: int) -> SeasonSnapshot:
    if not matches:
        raise ValueError("a season response must contain at least one match")

    first = matches[0]
    competition_key = (first.competition.id, first.competition.code)
    season_key = (first.season.id, first.season.start_date, first.season.end_date)
    if first.season.start_date.year != season_start_year:
        raise ValueError("the returned season does not match the requested start year")

    match_ids: set[int] = set()
    teams: dict[int, str] = {}
    records: list[MatchRecord] = []
    for match in matches:
        if (match.competition.id, match.competition.code) != competition_key:
            raise ValueError("all matches must belong to one competition")
        if (match.season.id, match.season.start_date, match.season.end_date) != season_key:
            raise ValueError("all matches must belong to one season")
        if match.id in match_ids:
            raise ValueError("match provider identifiers must be unique")
        match_ids.add(match.id)
        home_team = _to_team(match.home_team, teams)
        away_team = _to_team(match.away_team, teams)
        records.append(
            MatchRecord(
                provider_id=match.id,
                kickoff_at=match.utc_date,
                status=match.status,
                stage=match.stage,
                matchday=match.matchday,
                group_name=match.group_name,
                home_team=home_team,
                away_team=away_team,
                home_score=match.score.full_time.home,
                away_score=match.score.full_time.away,
                score_duration=match.score.duration,
            )
        )

    return SeasonSnapshot(
        competition=CompetitionRecord(
            provider_id=first.competition.id,
            code=first.competition.code,
            name=CHAMPIONS_LEAGUE_NAME,
        ),
        season=SeasonRecord(
            provider_id=first.season.id,
            start_date=first.season.start_date,
            end_date=first.season.end_date,
        ),
        matches=tuple(records),
    )


def _to_team(team: FootballDataTeam, known_teams: dict[int, str]) -> TeamRecord | None:
    if team.id is None and team.name is None:
        return None
    if team.id is None or team.name is None or not team.name.strip():
        raise ValueError("a known participant must have an identifier and name")
    previous_name = known_teams.setdefault(team.id, team.name)
    if previous_name != team.name:
        raise ValueError("one team identifier has conflicting names")
    return TeamRecord(provider_id=team.id, name=team.name)
