from io import StringIO

from alembic import command
from alembic.config import Config
from pytest import MonkeyPatch

from sport_events.settings import get_settings


def test_offline_migration_accepts_percent_encoded_database_url(
    monkeypatch: MonkeyPatch,
) -> None:
    database_url = (
        "postgresql+asyncpg://user:p%40ss@localhost:5432/sport_events"
        "?application_name=review%20test"
    )
    monkeypatch.setenv("SPORT_EVENTS_DATABASE_URL", database_url)
    get_settings.cache_clear()
    output = StringIO()
    config = Config("alembic.ini", output_buffer=output)

    try:
        command.upgrade(config, "head", sql=True)
        assert config.get_main_option("sqlalchemy.url") == database_url
        assert "CREATE TABLE alembic_version" in output.getvalue()
    finally:
        get_settings.cache_clear()
