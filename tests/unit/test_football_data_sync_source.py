import copy
import json
from pathlib import Path
from typing import Any

import pytest

from sport_events.football_data.errors import FootballDataResponseError
from sport_events.football_data.schemas import FootballDataMatch
from sport_events.football_data.sync_source import FootballDataChampionsLeagueSource

SAMPLES_PATH = Path(__file__).parents[1] / "fixtures" / "champions_league_matches.json"


def sample_match(name: str) -> dict[str, Any]:
    samples = json.loads(SAMPLES_PATH.read_text(encoding="utf-8"))["cases"]
    return copy.deepcopy(next(case["match"] for case in samples if case["name"] == name))


class StubClient:
    def __init__(self, matches: tuple[FootballDataMatch, ...]) -> None:
        self.matches = matches

    async def get_champions_league_matches(
        self, season_start_year: int
    ) -> tuple[FootballDataMatch, ...]:
        return self.matches


@pytest.mark.asyncio
async def test_maps_valid_response_and_preserves_unknown_participants() -> None:
    raw = sample_match("timed_league_stage")
    raw["homeTeam"] = {"id": None, "name": None}
    match = FootballDataMatch.model_validate(raw)

    snapshot = await FootballDataChampionsLeagueSource(StubClient((match,))).fetch_season(2026)

    assert snapshot.competition.provider_id == 2001
    assert snapshot.season.provider_id == 2557
    assert snapshot.matches[0].home_team is None
    assert snapshot.matches[0].away_team is not None
    assert snapshot.matches[0].home_score is None


@pytest.mark.parametrize(
    "case",
    [
        "empty",
        "duplicate",
        "wrong_season",
        "incomplete_team",
        "mixed_competition",
        "mixed_season",
        "conflicting_team",
    ],
)
@pytest.mark.asyncio
async def test_rejects_inconsistent_complete_response(case: str) -> None:
    raw = sample_match("timed_league_stage")
    matches = [FootballDataMatch.model_validate(raw)]
    if case == "empty":
        matches = []
    elif case == "duplicate":
        matches.append(FootballDataMatch.model_validate(raw))
    elif case == "wrong_season":
        raw["season"]["startDate"] = "2025-09-08"
        matches = [FootballDataMatch.model_validate(raw)]
    elif case == "incomplete_team":
        raw["homeTeam"] = {"id": 546, "name": None}
        matches = [FootballDataMatch.model_validate(raw)]
    elif case == "mixed_competition":
        other = copy.deepcopy(raw)
        other["id"] = 575342
        other["competition"]["id"] = 9999
        matches.append(FootballDataMatch.model_validate(other))
    elif case == "mixed_season":
        other = copy.deepcopy(raw)
        other["id"] = 575342
        other["season"]["id"] = 9999
        matches.append(FootballDataMatch.model_validate(other))
    else:
        other = copy.deepcopy(raw)
        other["id"] = 575342
        other["homeTeam"]["name"] = "Conflicting name"
        matches.append(FootballDataMatch.model_validate(other))

    source = FootballDataChampionsLeagueSource(StubClient(tuple(matches)))
    with pytest.raises(FootballDataResponseError, match="inconsistent season response"):
        await source.fetch_season(2026)
