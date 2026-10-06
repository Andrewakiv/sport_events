"""PostgreSQL-backed Champions League match queries."""

from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased
from sqlalchemy.sql.elements import ColumnElement

from sport_events.database.models.football import (
    FootballCompetition,
    FootballMatch,
    FootballSeason,
    FootballTeam,
)
from sport_events.football_models import Match, MatchFilters, MatchPage, Score, Season, Team


class ChampionsLeagueMatchQueries:
    """Execute match queries using a caller-owned session.

    The caller owns isolation and cleanup. Use a REPEATABLE READ transaction
    to keep the filtered count and page on the same snapshot.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_matches(self, query: MatchFilters) -> MatchPage:
        home_team = aliased(FootballTeam)
        away_team = aliased(FootballTeam)
        filters = _filters(query, home_team, away_team)
        statement = (
            select(FootballMatch, FootballSeason, home_team, away_team)
            .join(FootballSeason, FootballMatch.season_id == FootballSeason.id)
            .join(
                FootballCompetition,
                FootballSeason.competition_id == FootballCompetition.id,
            )
            .outerjoin(home_team, FootballMatch.home_team_id == home_team.id)
            .outerjoin(away_team, FootballMatch.away_team_id == away_team.id)
            .where(*filters)
            .order_by(FootballMatch.kickoff_at, FootballMatch.provider_id)
            .limit(query.limit)
            .offset(query.offset)
        )
        count_statement = (
            select(func.count(FootballMatch.id))
            .join(FootballSeason, FootballMatch.season_id == FootballSeason.id)
            .join(
                FootballCompetition,
                FootballSeason.competition_id == FootballCompetition.id,
            )
            .outerjoin(home_team, FootballMatch.home_team_id == home_team.id)
            .outerjoin(away_team, FootballMatch.away_team_id == away_team.id)
            .where(*filters)
        )
        total = await self._session.scalar(count_statement)
        rows = (await self._session.execute(statement)).all()
        return MatchPage(
            items=[_to_match(match, season, home, away) for match, season, home, away in rows],
            total=total or 0,
            limit=query.limit,
            offset=query.offset,
        )

    async def get_match(self, provider_id: int) -> Match | None:
        home_team = aliased(FootballTeam)
        away_team = aliased(FootballTeam)
        statement = (
            select(FootballMatch, FootballSeason, home_team, away_team)
            .join(FootballSeason, FootballMatch.season_id == FootballSeason.id)
            .join(
                FootballCompetition,
                FootballSeason.competition_id == FootballCompetition.id,
            )
            .outerjoin(home_team, FootballMatch.home_team_id == home_team.id)
            .outerjoin(away_team, FootballMatch.away_team_id == away_team.id)
            .where(
                FootballCompetition.code == "CL",
                FootballMatch.provider_id == provider_id,
            )
        )
        row = (await self._session.execute(statement)).one_or_none()
        if row is None:
            return None
        match, season, home, away = row
        return _to_match(match, season, home, away)


def _filters(
    query: MatchFilters,
    home_team: type[FootballTeam],
    away_team: type[FootballTeam],
) -> list[ColumnElement[bool]]:
    filters: list[ColumnElement[bool]] = [FootballCompetition.code == "CL"]
    if query.season is not None:
        filters.append(
            and_(
                FootballSeason.start_date >= date(query.season, 1, 1),
                FootballSeason.start_date < date(query.season + 1, 1, 1),
            )
        )
    if query.date is not None:
        start = datetime.combine(query.date, time.min, tzinfo=UTC)
        filters.append(FootballMatch.kickoff_at >= start)
        if query.date != date.max:
            filters.append(FootballMatch.kickoff_at < start + timedelta(days=1))
    if query.team_id is not None:
        filters.append(
            or_(
                home_team.provider_id == query.team_id,
                away_team.provider_id == query.team_id,
            )
        )
    if query.status is not None:
        filters.append(FootballMatch.status == query.status)
    return filters


def _to_match(
    match: FootballMatch,
    season: FootballSeason,
    home_team: FootballTeam | None,
    away_team: FootballTeam | None,
) -> Match:
    return Match(
        id=match.provider_id,
        season=Season(
            id=season.provider_id,
            start_date=season.start_date,
            end_date=season.end_date,
        ),
        kickoff_at=match.kickoff_at,
        status=match.status,
        stage=match.stage,
        matchday=match.matchday,
        group=match.group_name,
        home_team=_to_team(home_team),
        away_team=_to_team(away_team),
        score=(
            Score(home=match.home_score, away=match.away_score, duration=match.score_duration)
            if match.home_score is not None and match.away_score is not None
            else None
        ),
    )


def _to_team(team: FootballTeam | None) -> Team | None:
    if team is None:
        return None
    return Team(id=team.provider_id, name=team.name)
