"""Read-only tools that expose stored Champions League data to the language model."""

import datetime
import json
from collections.abc import Sequence
from typing import Annotated, Any, Protocol

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from sport_events.football_models import Match, MatchFilters, MatchPage, Team
from sport_events.match_chat.conversation import ToolCall, ToolDefinition, ToolResult


class MatchQueries(Protocol):
    async def list_matches(self, query: MatchFilters) -> MatchPage: ...

    async def get_match(self, provider_id: int) -> Match | None: ...

    async def find_teams(self, name: str, limit: int) -> list[Team]: ...


class _ToolArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FindTeamsArguments(_ToolArguments):
    name: Annotated[str, Field(min_length=2, max_length=100)]


class ListMatchesArguments(_ToolArguments):
    season: int | None = Field(
        default=None,
        ge=1900,
        le=2100,
        description="Calendar year in which the season starts, e.g. 2025 for 2025/26.",
    )
    date: datetime.date | None = Field(default=None, description="Kickoff day in UTC.")
    team_id: int | None = Field(
        default=None, gt=0, le=2_147_483_647, description="Team id from find_teams."
    )
    status: str | None = Field(
        default=None,
        min_length=1,
        max_length=30,
        description="Provider status such as SCHEDULED, TIMED, FINISHED, or POSTPONED.",
    )
    limit: int = Field(default=10, ge=1, le=25)
    offset: int = Field(default=0, ge=0, le=100_000)


class GetMatchArguments(_ToolArguments):
    match_id: int = Field(gt=0, le=2_147_483_647)


_LIST_MATCHES_DESCRIPTION = (
    "List Champions League matches, ordered by kickoff time ascending, with the total count. "
    "For upcoming matches filter by team_id and status TIMED or SCHEDULED. For the most recent "
    "results, call once with status FINISHED and limit 1 to read total, then call again with "
    "offset total minus the number of results wanted."
)


def _schema(arguments: type[BaseModel]) -> dict[str, Any]:
    schema = arguments.model_json_schema()
    schema.pop("title", None)
    return schema


class ChampionsLeagueTools:
    """Validate model-supplied arguments and run them against injected match queries."""

    def __init__(self, queries: MatchQueries) -> None:
        self._queries = queries

    @property
    def definitions(self) -> Sequence[ToolDefinition]:
        return (
            ToolDefinition(
                name="find_teams",
                description="Find teams by part of their name. Returns team ids and names.",
                input_schema=_schema(FindTeamsArguments),
            ),
            ToolDefinition(
                name="list_matches",
                description=_LIST_MATCHES_DESCRIPTION,
                input_schema=_schema(ListMatchesArguments),
            ),
            ToolDefinition(
                name="get_match",
                description="Get one match by its id, including stage, group, and score.",
                input_schema=_schema(GetMatchArguments),
            ),
        )

    async def execute(self, call: ToolCall) -> ToolResult:
        try:
            content = await self._run(call)
        except ValidationError as error:
            details = error.errors(include_url=False, include_input=False, include_context=False)
            return _error(call, f"Invalid arguments: {json.dumps(details, default=str)}")
        except LookupError as error:
            return _error(call, str(error))
        return ToolResult(call_id=call.id, content=content)

    async def _run(self, call: ToolCall) -> str:
        match call.name:
            case "find_teams":
                find = FindTeamsArguments.model_validate(call.arguments)
                teams = await self._queries.find_teams(find.name, 10)
                return json.dumps([team.model_dump() for team in teams])
            case "list_matches":
                listing = ListMatchesArguments.model_validate(call.arguments)
                page = await self._queries.list_matches(
                    MatchFilters.model_validate(listing.model_dump())
                )
                return page.model_dump_json()
            case "get_match":
                get = GetMatchArguments.model_validate(call.arguments)
                match = await self._queries.get_match(get.match_id)
                if match is None:
                    raise LookupError(f"No match with id {get.match_id}.")
                return match.model_dump_json()
            case _:
                raise LookupError(f"Unknown tool {call.name!r}.")


def _error(call: ToolCall, message: str) -> ToolResult:
    return ToolResult(call_id=call.id, content=message, is_error=True)
