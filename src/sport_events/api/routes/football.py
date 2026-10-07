"""Read-only Champions League match endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from sport_events.api.dependencies import get_match_queries
from sport_events.football_models import Match, MatchFilters, MatchPage
from sport_events.queries.champions_league_matches import ChampionsLeagueMatchQueries

router = APIRouter(prefix="/football/champions-league/matches", tags=["football"])


@router.get("", response_model=MatchPage)
async def list_matches(
    queries: Annotated[ChampionsLeagueMatchQueries, Depends(get_match_queries)],
    filters: Annotated[MatchFilters, Query()],
) -> MatchPage:
    return await queries.list_matches(filters)


@router.get("/{match_id}", response_model=Match)
async def get_match(
    match_id: Annotated[int, Path(gt=0, le=2_147_483_647)],
    queries: Annotated[ChampionsLeagueMatchQueries, Depends(get_match_queries)],
) -> Match:
    match = await queries.get_match(match_id)
    if match is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")
    return match
