import pytest
from sqlalchemy.exc import DBAPIError, InterfaceError, OperationalError

from sport_events.football_data.errors import (
    FootballDataAuthenticationError,
    FootballDataConfigurationError,
    FootballDataNetworkError,
    FootballDataProviderError,
    FootballDataRateLimitError,
    FootballDataResponseError,
    FootballDataTimeoutError,
)
from sport_events.football_sync.runs import FailureKind, SyncFailure
from sport_events.sync_jobs.failures import ChampionsLeagueSyncFailureClassifier

TRANSIENT = FailureKind.TRANSIENT
PERMANENT = FailureKind.PERMANENT


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (FootballDataTimeoutError("t"), SyncFailure(TRANSIENT, "provider request timed out")),
        (
            FootballDataNetworkError("n"),
            SyncFailure(TRANSIENT, "provider request failed before a response"),
        ),
        (
            FootballDataRateLimitError("r"),
            SyncFailure(TRANSIENT, "provider rate limit exceeded (HTTP 429)"),
        ),
        (
            FootballDataProviderError("p", status_code=503),
            SyncFailure(TRANSIENT, "provider returned HTTP 503"),
        ),
        (
            FootballDataProviderError("p", status_code=404),
            SyncFailure(PERMANENT, "provider returned HTTP 404"),
        ),
        (
            FootballDataConfigurationError("c"),
            SyncFailure(PERMANENT, "provider token is not configured"),
        ),
        (
            FootballDataAuthenticationError("a"),
            SyncFailure(PERMANENT, "provider rejected the token"),
        ),
        (
            FootballDataResponseError("x"),
            SyncFailure(PERMANENT, "provider returned invalid match data"),
        ),
        (
            OperationalError("SELECT 1", {}, Exception("down")),
            SyncFailure(TRANSIENT, "database is unavailable"),
        ),
        (
            InterfaceError("SELECT 1", {}, Exception("closed")),
            SyncFailure(TRANSIENT, "database is unavailable"),
        ),
        (ConnectionRefusedError(), SyncFailure(TRANSIENT, "database is unavailable")),
        (
            DBAPIError("SELECT 1", {}, Exception("lost"), connection_invalidated=True),
            SyncFailure(TRANSIENT, "database connection was lost"),
        ),
        (
            DBAPIError("SELECT 1", {}, Exception("constraint")),
            SyncFailure(PERMANENT, "unexpected error (DBAPIError)"),
        ),
        (ValueError("token=secret"), SyncFailure(PERMANENT, "unexpected error (ValueError)")),
    ],
)
def test_classifies_failures_with_safe_reasons(error: Exception, expected: SyncFailure) -> None:
    assert ChampionsLeagueSyncFailureClassifier().classify(error) == expected
