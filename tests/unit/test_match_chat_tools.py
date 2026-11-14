import json
from datetime import UTC, date, datetime

from sport_events.football_models import Match, MatchFilters, MatchPage, Season, Team
from sport_events.match_chat.conversation import ToolCall
from sport_events.match_chat.tools import ChampionsLeagueTools

MATCH = Match(
    id=575341,
    season=Season(id=2557, start_date=date(2026, 9, 8), end_date=date(2027, 6, 1)),
    kickoff_at=datetime(2026, 10, 13, 19, tzinfo=UTC),
    status="TIMED",
    stage="LEAGUE_STAGE",
    matchday=3,
    group=None,
    home_team=Team(id=81, name="FC Barcelona"),
    away_team=None,
    score=None,
)


class FakeQueries:
    def __init__(self) -> None:
        self.filters: list[MatchFilters] = []

    async def list_matches(self, query: MatchFilters) -> MatchPage:
        self.filters.append(query)
        return MatchPage(items=[MATCH], total=1, limit=query.limit, offset=query.offset)

    async def get_match(self, provider_id: int) -> Match | None:
        return MATCH if provider_id == MATCH.id else None

    async def find_teams(self, name: str, limit: int) -> list[Team]:
        return [Team(id=81, name="FC Barcelona")] if "barca" in name.lower() else []


def _call(tool: str, /, **arguments: object) -> ToolCall:
    return ToolCall(id="call-1", name=tool, arguments=dict(arguments))


async def test_definitions_expose_three_strict_object_schemas() -> None:
    definitions = ChampionsLeagueTools(FakeQueries()).definitions

    assert [tool.name for tool in definitions] == ["find_teams", "list_matches", "get_match"]
    for tool in definitions:
        assert tool.input_schema["type"] == "object"
        assert tool.input_schema["additionalProperties"] is False


async def test_find_teams_returns_json_and_empty_list_for_no_match() -> None:
    tools = ChampionsLeagueTools(FakeQueries())

    found = await tools.execute(_call("find_teams", name="Barca"))
    missing = await tools.execute(_call("find_teams", name="Nobody"))

    assert json.loads(found.content) == [{"id": 81, "name": "FC Barcelona"}]
    assert json.loads(missing.content) == []
    assert not found.is_error and not missing.is_error


async def test_list_matches_maps_arguments_to_filters_with_a_small_default_page() -> None:
    queries = FakeQueries()
    result = await ChampionsLeagueTools(queries).execute(
        _call("list_matches", team_id=81, status="TIMED", date="2026-10-13")
    )

    assert queries.filters == [
        MatchFilters(team_id=81, status="TIMED", date=date(2026, 10, 13), limit=10)
    ]
    assert json.loads(result.content)["total"] == 1
    assert result.call_id == "call-1"


async def test_get_match_returns_the_match() -> None:
    result = await ChampionsLeagueTools(FakeQueries()).execute(_call("get_match", match_id=575341))

    assert json.loads(result.content)["home_team"]["name"] == "FC Barcelona"


async def test_unknown_match_is_an_error_result() -> None:
    result = await ChampionsLeagueTools(FakeQueries()).execute(_call("get_match", match_id=1))

    assert result.is_error
    assert "No match with id 1" in result.content


async def test_invalid_arguments_are_an_error_result_without_echoing_input() -> None:
    tools = ChampionsLeagueTools(FakeQueries())

    too_large = await tools.execute(_call("list_matches", limit=500))
    extra = await tools.execute(_call("find_teams", name="Barca", sql="DROP TABLE"))
    short = await tools.execute(_call("find_teams", name="B"))

    for result in (too_large, extra, short):
        assert result.is_error
        assert result.content.startswith("Invalid arguments:")
    assert "DROP TABLE" not in extra.content


async def test_unknown_tool_is_an_error_result() -> None:
    result = await ChampionsLeagueTools(FakeQueries()).execute(_call("delete_everything"))

    assert result.is_error
