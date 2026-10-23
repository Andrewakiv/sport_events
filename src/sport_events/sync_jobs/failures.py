"""Classify Champions League sync failures as transient or permanent."""

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


class ChampionsLeagueSyncFailureClassifier:
    """Reasons are fixed texts so that tokens, URLs, and payloads never reach the journal."""

    def classify(self, error: Exception) -> SyncFailure:
        match error:
            case FootballDataConfigurationError():
                return _permanent("provider token is not configured")
            case FootballDataAuthenticationError():
                return _permanent("provider rejected the token")
            case FootballDataRateLimitError():
                return _transient("provider rate limit exceeded (HTTP 429)")
            case FootballDataTimeoutError():
                return _transient("provider request timed out")
            case FootballDataNetworkError():
                return _transient("provider request failed before a response")
            case FootballDataProviderError(status_code=status) if status >= 500:
                return _transient(f"provider returned HTTP {status}")
            case FootballDataProviderError(status_code=status):
                return _permanent(f"provider returned HTTP {status}")
            case FootballDataResponseError():
                return _permanent("provider returned invalid match data")
            case OperationalError() | InterfaceError() | OSError():
                return _transient("database is unavailable")
            case DBAPIError(connection_invalidated=True):
                return _transient("database connection was lost")
            case _:
                return _permanent(f"unexpected error ({type(error).__name__})")


def _transient(reason: str) -> SyncFailure:
    return SyncFailure(FailureKind.TRANSIENT, reason)


def _permanent(reason: str) -> SyncFailure:
    return SyncFailure(FailureKind.PERMANENT, reason)
