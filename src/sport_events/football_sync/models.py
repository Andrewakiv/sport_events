"""Provider-neutral records used by the Champions League synchronization operation."""

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class CompetitionRecord:
    provider_id: int
    code: str
    name: str


@dataclass(frozen=True)
class SeasonRecord:
    provider_id: int
    start_date: date
    end_date: date


@dataclass(frozen=True)
class TeamRecord:
    provider_id: int
    name: str


@dataclass(frozen=True)
class MatchRecord:
    provider_id: int
    kickoff_at: datetime
    status: str
    stage: str
    matchday: int | None
    group_name: str | None
    home_team: TeamRecord | None
    away_team: TeamRecord | None
    home_score: int | None
    away_score: int | None
    score_duration: str | None


@dataclass(frozen=True)
class SeasonSnapshot:
    competition: CompetitionRecord
    season: SeasonRecord
    matches: tuple[MatchRecord, ...]


@dataclass(frozen=True)
class SyncResult:
    matches_processed: int
