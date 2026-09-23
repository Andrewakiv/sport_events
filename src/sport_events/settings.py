from functools import lru_cache

from pydantic import Field
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


@lru_cache
def get_settings() -> Settings:
    return Settings()
