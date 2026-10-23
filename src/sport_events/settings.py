from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="SPORT_EVENTS_",
        extra="ignore",
    )

    app_name: str = "Sport Events API"
    environment: str = "local"
    database_url: str = Field(
        default="postgresql+asyncpg://sport_events:sport_events@localhost:5432/sport_events",
    )
    football_data_api_token: SecretStr | None = Field(
        default=None,
        validation_alias="FOOTBALL_DATA_API_TOKEN",
        repr=False,
    )
    # Only this season is polled on the schedule; completed seasons are backfilled manually.
    champions_league_sync_season: int | None = Field(default=None, ge=2000, le=2100)
    champions_league_sync_cron: str = "0 */6 * * *"
    champions_league_sync_max_attempts: int = Field(default=3, ge=1, le=10)
    champions_league_sync_retry_base_seconds: int = Field(default=30, ge=1)
    champions_league_sync_retry_max_seconds: int = Field(default=300, ge=1)
    sync_worker_stalled_after_seconds: int = Field(default=60, ge=30)


@lru_cache
def get_settings() -> Settings:
    return Settings()
