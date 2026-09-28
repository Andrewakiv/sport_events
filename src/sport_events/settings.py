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


@lru_cache
def get_settings() -> Settings:
    return Settings()
