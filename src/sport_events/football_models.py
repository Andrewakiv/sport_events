"""Shared validation and response models for the football read API."""

import datetime

from pydantic import BaseModel, Field


class MatchFilters(BaseModel):
    season: int | None = Field(default=None, ge=1900, le=2100)
    date: datetime.date | None = None
    team_id: int | None = Field(default=None, gt=0, le=2_147_483_647)
    status: str | None = Field(default=None, min_length=1)
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0, le=9_223_372_036_854_775_807)


class Team(BaseModel):
    id: int
    name: str


class Season(BaseModel):
    id: int
    start_date: datetime.date
    end_date: datetime.date


class Score(BaseModel):
    home: int
    away: int
    duration: str | None


class Match(BaseModel):
    id: int
    season: Season
    kickoff_at: datetime.datetime
    status: str
    stage: str
    matchday: int | None
    group: str | None
    home_team: Team | None
    away_team: Team | None
    score: Score | None


class MatchPage(BaseModel):
    items: list[Match]
    total: int
    limit: int
    offset: int
