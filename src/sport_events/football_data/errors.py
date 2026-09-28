"""Failures exposed by the football-data.org client."""


class FootballDataClientError(Exception):
    """Base class for failures fetching provider matches."""


class FootballDataConfigurationError(FootballDataClientError):
    """The provider token has not been configured."""


class FootballDataAuthenticationError(FootballDataClientError):
    """The provider rejected the configured token."""


class FootballDataRateLimitError(FootballDataClientError):
    """The provider refused the request due to its rate limit."""


class FootballDataNetworkError(FootballDataClientError):
    """The request failed before receiving a provider response."""


class FootballDataTimeoutError(FootballDataNetworkError):
    """The provider request timed out."""


class FootballDataProviderError(FootballDataClientError):
    """The provider returned an unexpected HTTP error."""


class FootballDataResponseError(FootballDataClientError):
    """The provider returned an invalid match-list response."""
