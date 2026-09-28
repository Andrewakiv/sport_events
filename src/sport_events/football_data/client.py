"""HTTP client for the football-data.org Champions League match list."""

import httpx

from sport_events.football_data.errors import (
    FootballDataAuthenticationError,
    FootballDataConfigurationError,
    FootballDataNetworkError,
    FootballDataProviderError,
    FootballDataRateLimitError,
    FootballDataResponseError,
    FootballDataTimeoutError,
)
from sport_events.football_data.match_data import FootballDataMatch, FootballDataMatchesResponse
from sport_events.settings import Settings

MATCHES_URL = "https://api.football-data.org/v4/competitions/CL/matches"
REQUEST_TIMEOUT = httpx.Timeout(10.0, connect=5.0)


class FootballDataClient:
    """Fetch typed match data; the caller owns the supplied HTTP client."""

    def __init__(self, *, settings: Settings, http_client: httpx.AsyncClient) -> None:
        token = settings.football_data_api_token
        if token is None or not token.get_secret_value():
            raise FootballDataConfigurationError("FOOTBALL_DATA_API_TOKEN is not configured")
        self._token = token
        self._http_client = http_client

    async def get_champions_league_matches(
        self, season_start_year: int
    ) -> tuple[FootballDataMatch, ...]:
        """Return every match for one season, or raise a classified failure."""
        try:
            response = await self._http_client.get(
                MATCHES_URL,
                params={"season": season_start_year},
                headers={"X-Auth-Token": self._token.get_secret_value()},
                timeout=REQUEST_TIMEOUT,
            )
        except httpx.TimeoutException as exc:
            raise FootballDataTimeoutError("football-data.org request timed out") from exc
        except httpx.RequestError as exc:
            raise FootballDataNetworkError("football-data.org request failed") from exc

        status = response.status_code
        if status in (401, 403):
            raise FootballDataAuthenticationError(
                f"football-data.org rejected the token (HTTP {status})"
            )
        if status == 429:
            raise FootballDataRateLimitError("football-data.org rate limit exceeded (HTTP 429)")
        if status >= 400:
            raise FootballDataProviderError(f"football-data.org returned HTTP {status}")

        try:
            parsed = FootballDataMatchesResponse.model_validate(response.json())
        except ValueError as exc:
            raise FootballDataResponseError(
                "football-data.org returned malformed match data"
            ) from exc
        return tuple(parsed.matches)
