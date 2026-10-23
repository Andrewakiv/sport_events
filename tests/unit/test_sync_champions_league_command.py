import sys
from unittest.mock import AsyncMock

import pytest

from sport_events.commands import sync_champions_league


def test_main_queues_requested_season(monkeypatch: pytest.MonkeyPatch) -> None:
    run = AsyncMock(return_value=0)
    monkeypatch.setattr(sync_champions_league, "_run", run)
    monkeypatch.setattr(sys, "argv", ["sync-champions-league", "2026"])

    with pytest.raises(SystemExit) as exited:
        sync_champions_league.main()

    assert exited.value.code == 0
    run.assert_awaited_once_with(2026)
