from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import aliased

from sport_events.database.football_read import _filters, _to_view
from sport_events.database.models.football import FootballMatch, FootballSeason, FootballTeam
from sport_events.football_read.models import MatchListQuery, TeamView


def test_query_filters_use_half_open_utc_day_and_season_ranges() -> None:
    filters = _filters(
        MatchListQuery(
            season_start_year=2026,
            match_date=date(2026, 10, 13),
            team_provider_id=498,
            status="TIMED",
        ),
        aliased(FootballTeam),
        aliased(FootballTeam),
    )
    statement = select(FootballMatch).where(*filters).compile(dialect=postgresql.dialect())
    assert statement.params == {
        "code_1": "CL",
        "start_date_1": date(2026, 1, 1),
        "start_date_2": date(2027, 1, 1),
        "kickoff_at_1": datetime(2026, 10, 13, tzinfo=UTC),
        "kickoff_at_2": datetime(2026, 10, 14, tzinfo=UTC),
        "provider_id_1": 498,
        "provider_id_2": 498,
        "status_1": "TIMED",
    }


def test_maximum_date_filter_does_not_overflow() -> None:
    filters = _filters(
        MatchListQuery(match_date=date.max), aliased(FootballTeam), aliased(FootballTeam)
    )
    statement = select(FootballMatch).where(*filters).compile(dialect=postgresql.dialect())
    assert statement.params == {
        "code_1": "CL",
        "kickoff_at_1": datetime(9999, 12, 31, tzinfo=UTC),
    }


def test_projection_preserves_nullable_participants_and_scores() -> None:
    season = FootballSeason(
        provider_id=2557, start_date=date(2026, 9, 8), end_date=date(2027, 1, 27)
    )
    match = FootballMatch(
        provider_id=575341,
        kickoff_at=datetime(2026, 10, 13, tzinfo=UTC),
        status="TIMED",
        stage="LAST_16",
        matchday=None,
        group_name=None,
        home_score=None,
        away_score=None,
        score_duration=None,
    )
    away = FootballTeam(provider_id=498, name="Sporting Clube de Portugal")
    view = _to_view(match, season, None, away)
    assert view.provider_id == 575341
    assert view.season.provider_id == 2557
    assert view.home_team is None
    assert view.away_team == TeamView(498, "Sporting Clube de Portugal")
    assert view.home_score is None and view.away_score is None
    assert view.status == "TIMED" and view.stage == "LAST_16"
