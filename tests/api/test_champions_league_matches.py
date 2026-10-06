from collections.abc import AsyncIterator
from dataclasses import replace
from datetime import UTC, date, datetime

import pytest
from httpx import ASGITransport, AsyncClient

from sport_events.football_read.models import (
    MatchListQuery,
    MatchPage,
    MatchView,
    SeasonView,
    TeamView,
)
from sport_events.main import create_app


class StubDatabase:
    async def close(self) -> None:
        pass


class StubMatchReader:
    def __init__(self, *, page: MatchPage, match: MatchView | None = None) -> None:
        self.page = page
        self.match = match
        self.queries: list[MatchListQuery] = []
        self.match_ids: list[int] = []

    async def list_matches(self, query: MatchListQuery) -> MatchPage:
        self.queries.append(query)
        return self.page

    async def get_match(self, provider_id: int) -> MatchView | None:
        self.match_ids.append(provider_id)
        return self.match


async def client_for(reader: StubMatchReader) -> AsyncIterator[AsyncClient]:
    app = create_app(database=StubDatabase(), football_match_reader=reader)  # type: ignore[arg-type]
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


def scheduled_match() -> MatchView:
    return MatchView(
        provider_id=575341,
        season=SeasonView(2557, date(2026, 9, 8), date(2027, 1, 27)),
        kickoff_at=datetime(2026, 10, 13, 16, 45, tzinfo=UTC),
        status="TIMED",
        stage="LEAGUE_STAGE",
        matchday=2,
        group_name=None,
        home_team=None,
        away_team=TeamView(498, "Sporting Clube de Portugal"),
        home_score=None,
        away_score=None,
        score_duration=None,
    )


async def test_lists_matches_with_filters_pagination_and_nullable_score() -> None:
    match = scheduled_match()
    reader = StubMatchReader(page=MatchPage((match,), total=3, limit=1, offset=1))
    async for client in client_for(reader):
        response = await client.get(
            "/api/v1/football/champions-league/matches",
            params={
                "season": 2026,
                "date": "2026-10-13",
                "team_id": 498,
                "status": "TIMED",
                "limit": 1,
                "offset": 1,
            },
        )

    assert response.status_code == 200
    assert reader.queries == [
        MatchListQuery(
            season_start_year=2026,
            match_date=date(2026, 10, 13),
            team_provider_id=498,
            status="TIMED",
            limit=1,
            offset=1,
        )
    ]
    assert response.json() == {
        "items": [
            {
                "id": 575341,
                "season": {
                    "id": 2557,
                    "start_date": "2026-09-08",
                    "end_date": "2027-01-27",
                },
                "kickoff_at": "2026-10-13T16:45:00Z",
                "status": "TIMED",
                "stage": "LEAGUE_STAGE",
                "matchday": 2,
                "group": None,
                "home_team": None,
                "away_team": {"id": 498, "name": "Sporting Clube de Portugal"},
                "score": None,
            }
        ],
        "total": 3,
        "limit": 1,
        "offset": 1,
    }


async def test_returns_match_detail_with_stored_stage_status_and_score() -> None:
    match = replace(
        scheduled_match(),
        status="FINISHED",
        stage="LAST_16",
        home_team=TeamView(546, "Racing Club de Lens"),
        home_score=2,
        away_score=1,
        score_duration="REGULAR",
    )
    reader = StubMatchReader(page=MatchPage((), 0, 50, 0), match=match)
    async for client in client_for(reader):
        response = await client.get("/api/v1/football/champions-league/matches/575341")

    assert response.status_code == 200
    assert reader.match_ids == [575341]
    assert response.json()["stage"] == "LAST_16"
    assert response.json()["status"] == "FINISHED"
    assert response.json()["score"] == {"home": 2, "away": 1, "duration": "REGULAR"}


async def test_returns_not_found_for_unknown_match() -> None:
    reader = StubMatchReader(page=MatchPage((), 0, 50, 0))
    async for client in client_for(reader):
        response = await client.get("/api/v1/football/champions-league/matches/999999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Match not found"}


@pytest.mark.parametrize(
    "params",
    [
        {"limit": 101},
        {"limit": 0},
        {"offset": -1},
        {"season": 2101},
        {"date": "not-a-date"},
        {"team_id": 0},
        {"team_id": 2_147_483_648},
        {"offset": 9_223_372_036_854_775_808},
        {"status": ""},
    ],
)
async def test_rejects_invalid_filters_before_querying(
    params: dict[str, str | int],
) -> None:
    reader = StubMatchReader(page=MatchPage((), 0, 50, 0))
    async for client in client_for(reader):
        response = await client.get("/api/v1/football/champions-league/matches", params=params)

    assert response.status_code == 422
    assert reader.queries == []


async def test_returns_empty_page_with_default_query() -> None:
    reader = StubMatchReader(page=MatchPage((), 0, 50, 0))
    async for client in client_for(reader):
        response = await client.get("/api/v1/football/champions-league/matches")

    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0, "limit": 50, "offset": 0}
    assert reader.queries == [MatchListQuery()]


@pytest.mark.parametrize("match_id", ["0", "-1", "2147483648", "invalid"])
async def test_rejects_invalid_match_id_before_querying(match_id: str) -> None:
    reader = StubMatchReader(page=MatchPage((), 0, 50, 0))
    async for client in client_for(reader):
        response = await client.get(f"/api/v1/football/champions-league/matches/{match_id}")
    assert response.status_code == 422
    assert reader.match_ids == []
