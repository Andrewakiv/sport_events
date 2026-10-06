"""Public Champions League match response schemas."""

from datetime import date, datetime

from pydantic import BaseModel

from sport_events.football_read.models import MatchPage, MatchView, SeasonView, TeamView


class FootballTeamResponse(BaseModel):
    id: int
    name: str

    @classmethod
    def from_view(cls, team: TeamView) -> "FootballTeamResponse":
        return cls(id=team.provider_id, name=team.name)


class FootballSeasonResponse(BaseModel):
    id: int
    start_date: date
    end_date: date

    @classmethod
    def from_view(cls, season: SeasonView) -> "FootballSeasonResponse":
        return cls(id=season.provider_id, start_date=season.start_date, end_date=season.end_date)


class FootballScoreResponse(BaseModel):
    home: int
    away: int
    duration: str | None


class FootballMatchResponse(BaseModel):
    id: int
    season: FootballSeasonResponse
    kickoff_at: datetime
    status: str
    stage: str
    matchday: int | None
    group: str | None
    home_team: FootballTeamResponse | None
    away_team: FootballTeamResponse | None
    score: FootballScoreResponse | None

    @classmethod
    def from_view(cls, match: MatchView) -> "FootballMatchResponse":
        score = None
        if match.home_score is not None and match.away_score is not None:
            score = FootballScoreResponse(
                home=match.home_score, away=match.away_score, duration=match.score_duration
            )
        return cls(
            id=match.provider_id,
            season=FootballSeasonResponse.from_view(match.season),
            kickoff_at=match.kickoff_at,
            status=match.status,
            stage=match.stage,
            matchday=match.matchday,
            group=match.group_name,
            home_team=(
                FootballTeamResponse.from_view(match.home_team)
                if match.home_team is not None
                else None
            ),
            away_team=(
                FootballTeamResponse.from_view(match.away_team)
                if match.away_team is not None
                else None
            ),
            score=score,
        )


class FootballMatchListResponse(BaseModel):
    items: list[FootballMatchResponse]
    total: int
    limit: int
    offset: int

    @classmethod
    def from_page(cls, page: MatchPage) -> "FootballMatchListResponse":
        return cls(
            items=[FootballMatchResponse.from_view(match) for match in page.items],
            total=page.total,
            limit=page.limit,
            offset=page.offset,
        )
