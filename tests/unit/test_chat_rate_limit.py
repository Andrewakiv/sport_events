import pytest

from sport_events.match_chat.rate_limit import SlidingWindowRateLimiter


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def test_allows_up_to_the_limit_then_reports_seconds_to_wait() -> None:
    clock = Clock()
    limiter = SlidingWindowRateLimiter(2, 60, clock)

    assert limiter.check("a") is None
    clock.now += 10
    assert limiter.check("a") is None
    clock.now += 10
    assert limiter.check("a") == 40


def test_requests_expire_after_the_window() -> None:
    clock = Clock()
    limiter = SlidingWindowRateLimiter(1, 60, clock)
    assert limiter.check("a") is None

    clock.now += 60

    assert limiter.check("a") is None


def test_keys_are_limited_independently() -> None:
    limiter = SlidingWindowRateLimiter(1, 60, Clock())

    assert limiter.check("a") is None
    assert limiter.check("b") is None
    assert limiter.check("a") is not None


def test_rejected_requests_do_not_extend_the_block() -> None:
    clock = Clock()
    limiter = SlidingWindowRateLimiter(1, 60, clock)
    limiter.check("a")
    clock.now += 30
    assert limiter.check("a") == 30

    clock.now += 30

    assert limiter.check("a") is None


def test_drops_idle_keys_to_bound_memory_and_fails_closed_when_full() -> None:
    clock = Clock()
    limiter = SlidingWindowRateLimiter(1, 60, clock, max_keys=2)
    limiter.check("a")
    limiter.check("b")

    # Both keys are still active: a new client is refused instead of growing the table.
    assert limiter.check("c") == 60

    clock.now += 61

    assert limiter.check("c") is None
    assert limiter.check("a") is None


@pytest.mark.parametrize(("requests", "window", "keys"), [(0, 60, 1), (1, 0, 1), (1, 60, 0)])
def test_rejects_non_positive_limits(requests: int, window: float, keys: int) -> None:
    with pytest.raises(ValueError, match="positive"):
        SlidingWindowRateLimiter(requests, window, max_keys=keys)
