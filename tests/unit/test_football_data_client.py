"""Provider boundary tests; all HTTP responses are local and token-free."""

import copy
import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from sport_events.football_data.client import (
    FootballDataAuthenticationError,
    FootballDataClient,
    FootballDataConfigurationError,
    FootballDataNetworkError,
    FootballDataProviderError,
    FootballDataRateLimitError,
    FootballDataResponseError,
    FootballDataTimeoutError,
)
from sport_events.settings import Settings

SAMPLES_PATH = Path(__file__).parents[1] / "fixtures" / "champions_league_matches.json"


def sample_match(name: str) -> dict[str, Any]:
    samples = json.loads(SAMPLES_PATH.read_text(encoding="utf-8"))["cases"]
    return copy.deepcopy(next(case["match"] for case in samples if case["name"] == name))


def configured_settings(monkeypatch: pytest.MonkeyPatch) -> Settings:
    monkeypatch.setenv("FOOTBALL_DATA_API_TOKEN", "test-token")
    return Settings(_env_file=None)


@pytest.mark.asyncio
async def test_fetches_finished_and_scheduled_matches(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = configured_settings(monkeypatch)
    scheduled = sample_match("timed_league_stage")
    scheduled["homeTeam"] = {"id": None, "name": None}
    finished = sample_match("finished_league_stage")

    def respond(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == (
            "https://api.football-data.org/v4/competitions/CL/matches?season=2026"
        )
        assert request.headers["X-Auth-Token"] == "test-token"
        assert request.extensions["timeout"]["connect"] == 5.0
        assert request.extensions["timeout"]["read"] == 10.0
        return httpx.Response(200, json={"matches": [scheduled, finished]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as http_client:
        client = FootballDataClient(settings=settings, http_client=http_client)
        matches = await client.get_champions_league_matches(2026)

    assert len(matches) == 2
    assert matches[0].id == 575341
    assert matches[0].home_team.id is None
    assert matches[0].group_name is None
    assert matches[0].score.full_time.home is None
    assert matches[0].score.full_time.away is None
    assert matches[1].id == 575323
    assert matches[1].season.id == 2557
    assert matches[1].home_team.id == 851
    assert matches[1].score.full_time.home == 2
    assert matches[1].score.full_time.away == 3


@pytest.mark.parametrize(
    ("status", "expected_error"),
    [
        (401, FootballDataAuthenticationError),
        (403, FootballDataAuthenticationError),
        (429, FootballDataRateLimitError),
        (502, FootballDataProviderError),
    ],
)
@pytest.mark.asyncio
async def test_classifies_http_failures(
    monkeypatch: pytest.MonkeyPatch,
    status: int,
    expected_error: type[Exception],
) -> None:
    settings = configured_settings(monkeypatch)

    def respond(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json={"message": "provider error"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as http_client:
        client = FootballDataClient(settings=settings, http_client=http_client)
        with pytest.raises(expected_error) as error:
            await client.get_champions_league_matches(2026)

    assert "test-token" not in str(error.value)


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"matches": None},
        {"matches": [sample_match("finished_league_stage"), {"id": 1}]},
        {"matches": [{**sample_match("finished_league_stage"), "id": "575323"}]},
        {
            "matches": [
                {
                    **sample_match("finished_league_stage"),
                    "score": {"duration": "REGULAR", "fullTime": {"home": 1, "away": None}},
                }
            ]
        },
    ],
)
@pytest.mark.asyncio
async def test_rejects_incomplete_responses(
    monkeypatch: pytest.MonkeyPatch, body: dict[str, Any]
) -> None:
    settings = configured_settings(monkeypatch)

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=body))
    ) as http_client:
        client = FootballDataClient(settings=settings, http_client=http_client)
        with pytest.raises(FootballDataResponseError):
            await client.get_champions_league_matches(2026)


@pytest.mark.asyncio
async def test_rejects_invalid_json(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = configured_settings(monkeypatch)

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, text="{"))
    ) as http_client:
        client = FootballDataClient(settings=settings, http_client=http_client)
        with pytest.raises(FootballDataResponseError):
            await client.get_champions_league_matches(2026)


@pytest.mark.parametrize(
    ("raised", "expected_error"),
    [
        (httpx.ReadTimeout("timed out"), FootballDataTimeoutError),
        (httpx.ConnectError("connection failed"), FootballDataNetworkError),
    ],
)
@pytest.mark.asyncio
async def test_classifies_transport_failures(
    monkeypatch: pytest.MonkeyPatch,
    raised: Exception,
    expected_error: type[Exception],
) -> None:
    settings = configured_settings(monkeypatch)

    def fail(request: httpx.Request) -> httpx.Response:
        raise raised

    async with httpx.AsyncClient(transport=httpx.MockTransport(fail)) as http_client:
        client = FootballDataClient(settings=settings, http_client=http_client)
        with pytest.raises(expected_error):
            await client.get_champions_league_matches(2026)


@pytest.mark.asyncio
async def test_missing_token_is_a_configuration_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FOOTBALL_DATA_API_TOKEN", raising=False)
    settings = Settings(_env_file=None)

    async with httpx.AsyncClient() as http_client:
        with pytest.raises(FootballDataConfigurationError, match="FOOTBALL_DATA_API_TOKEN"):
            FootballDataClient(settings=settings, http_client=http_client)
