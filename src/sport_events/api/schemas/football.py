"""Public Champions League match response schemas."""

from datetime import date, datetime

from pydantic import BaseModel


class FootballTeamResponse(BaseModel):
    id: int
    name: str


class FootballSeasonResponse(BaseModel):
    id: int
    start_date: date
    end_date: date


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


class FootballMatchListResponse(BaseModel):
    items: list[FootballMatchResponse]
    total: int
    limit: int
    offset: int
