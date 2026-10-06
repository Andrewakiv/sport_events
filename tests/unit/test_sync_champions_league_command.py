import sys
from unittest.mock import AsyncMock

import pytest

from sport_events.commands import sync_champions_league


def test_main_runs_requested_season(monkeypatch: pytest.MonkeyPatch) -> None:
    run = AsyncMock()
    monkeypatch.setattr(sync_champions_league, "_run", run)
    monkeypatch.setattr(sys, "argv", ["sync-champions-league", "2026"])

    sync_champions_league.main()

    run.assert_awaited_once_with(2026)
