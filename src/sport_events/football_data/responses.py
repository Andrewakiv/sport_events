"""Typed fields used from football-data.org match-list responses."""

from datetime import date

from pydantic import (
    AwareDatetime,
    BaseModel,
    Field,
    StrictStr,
    model_validator,
)


class FootballDataCompetition(BaseModel):
    id: int = Field(strict=True, gt=0)
    code: StrictStr


class FootballDataSeason(BaseModel):
    id: int = Field(strict=True, gt=0)
    start_date: date = Field(validation_alias="startDate")
    end_date: date = Field(validation_alias="endDate")


class FootballDataTeam(BaseModel):
    id: int | None = Field(strict=True, gt=0)
    name: StrictStr | None


class FootballDataFullTimeScore(BaseModel):
    home: int | None = Field(strict=True, ge=0)
    away: int | None = Field(strict=True, ge=0)

    @model_validator(mode="after")
    def require_score_pair(self) -> "FootballDataFullTimeScore":
        if (self.home is None) != (self.away is None):
            raise ValueError("full-time scores must both be present or both be null")
        return self


class FootballDataScore(BaseModel):
    duration: StrictStr | None
    full_time: FootballDataFullTimeScore = Field(validation_alias="fullTime")


class FootballDataMatch(BaseModel):
    id: int = Field(strict=True, gt=0)
    competition: FootballDataCompetition
    season: FootballDataSeason
    utc_date: AwareDatetime = Field(validation_alias="utcDate")
    status: StrictStr
    stage: StrictStr
    matchday: int | None = Field(strict=True, ge=0)
    group_name: StrictStr | None = Field(validation_alias="group")
    last_updated: AwareDatetime = Field(validation_alias="lastUpdated")
    home_team: FootballDataTeam = Field(validation_alias="homeTeam")
    away_team: FootballDataTeam = Field(validation_alias="awayTeam")
    score: FootballDataScore


class FootballDataMatchesResponse(BaseModel):
    matches: list[FootballDataMatch]
