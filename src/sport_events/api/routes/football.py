"""Read-only Champions League match endpoints."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from sport_events.api.dependencies import get_match_reader
from sport_events.api.schemas.football import (
    FootballMatchListResponse,
    FootballMatchResponse,
)
from sport_events.football_read.models import (
    FootballMatchReader,
    MatchListQuery,
)

router = APIRouter(prefix="/football/champions-league/matches", tags=["football"])


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
    return FootballMatchListResponse.from_page(page)


@router.get("/{match_id}", response_model=FootballMatchResponse)
async def get_match(
    match_id: Annotated[int, Path(gt=0, le=2_147_483_647)],
    reader: Annotated[FootballMatchReader, Depends(get_match_reader)],
) -> FootballMatchResponse:
    match = await reader.get_match(match_id)
    if match is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")
    return FootballMatchResponse.from_view(match)
