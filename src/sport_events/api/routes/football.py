"""Read-only Champions League match endpoints."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, status

from sport_events.api.schemas.football import (
    FootballMatchListResponse,
    FootballMatchResponse,
    FootballScoreResponse,
    FootballSeasonResponse,
    FootballTeamResponse,
)
from sport_events.database.connection import Database
from sport_events.database.football_read import PostgresFootballMatchReader
from sport_events.football_read.models import (
    FootballMatchReader,
    MatchListQuery,
    MatchView,
    TeamView,
)

router = APIRouter(prefix="/football/champions-league/matches", tags=["football"])


def get_match_reader(request: Request) -> FootballMatchReader:
    configured_reader: FootballMatchReader | None = request.app.state.football_match_reader
    if configured_reader is not None:
        return configured_reader
    database: Database = request.app.state.database
    return PostgresFootballMatchReader(database.engine)


@router.get("", response_model=FootballMatchListResponse)
async def list_matches(
    reader: Annotated[FootballMatchReader, Depends(get_match_reader)],
    season: Annotated[int | None, Query(ge=1900, le=2100)] = None,
    match_date: Annotated[date | None, Query(alias="date")] = None,
    team_id: Annotated[int | None, Query(gt=0, le=2_147_483_647)] = None,
    match_status: Annotated[str | None, Query(alias="status", min_length=1)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0, le=9_223_372_036_854_775_807)] = 0,
) -> FootballMatchListResponse:
    page = await reader.list_matches(
        MatchListQuery(
            season_start_year=season,
            match_date=match_date,
            team_provider_id=team_id,
            status=match_status,
            limit=limit,
            offset=offset,
        )
    )
    return FootballMatchListResponse(
        items=[_match_response(item) for item in page.items],
        total=page.total,
        limit=page.limit,
        offset=page.offset,
    )


@router.get("/{match_id}", response_model=FootballMatchResponse)
async def get_match(
    match_id: Annotated[int, Path(gt=0, le=2_147_483_647)],
    reader: Annotated[FootballMatchReader, Depends(get_match_reader)],
) -> FootballMatchResponse:
    match = await reader.get_match(match_id)
    if match is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")
    return _match_response(match)


def _match_response(match: MatchView) -> FootballMatchResponse:
    score = None
    if match.home_score is not None and match.away_score is not None:
        score = FootballScoreResponse(
            home=match.home_score,
            away=match.away_score,
            duration=match.score_duration,
        )
    return FootballMatchResponse(
        id=match.provider_id,
        season=FootballSeasonResponse(
            id=match.season.provider_id,
            start_date=match.season.start_date,
            end_date=match.season.end_date,
        ),
        kickoff_at=match.kickoff_at,
        status=match.status,
        stage=match.stage,
        matchday=match.matchday,
        group=match.group_name,
        home_team=_team_response(match.home_team),
        away_team=_team_response(match.away_team),
        score=score,
    )


def _team_response(team: TeamView | None) -> FootballTeamResponse | None:
    if team is None:
        return None
    return FootballTeamResponse(id=team.provider_id, name=team.name)
