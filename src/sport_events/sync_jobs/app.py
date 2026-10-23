"""Procrastinate application whose queue lives in the project's PostgreSQL database."""

import procrastinate
from sqlalchemy.engine import make_url

from sport_events.settings import get_settings


def queue_conninfo(database_url: str) -> str:
    """Convert the SQLAlchemy asyncpg URL into the libpq URL psycopg expects."""
    return make_url(database_url).set(drivername="postgresql").render_as_string(hide_password=False)


app = procrastinate.App(
    connector=procrastinate.PsycopgConnector(conninfo=queue_conninfo(get_settings().database_url)),
    import_paths=["sport_events.sync_jobs.tasks"],
)
