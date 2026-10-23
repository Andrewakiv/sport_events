from pathlib import Path

from procrastinate.schema import SchemaManager

VENDORED_SCHEMA = Path("migrations/sql/procrastinate_3.10.0_schema.sql")
PROVENANCE_LINES = 2


def test_vendored_schema_matches_installed_procrastinate() -> None:
    # Line endings depend on the checkout (core.autocrlf), not on the schema.
    vendored = VENDORED_SCHEMA.read_text(encoding="utf-8").replace("\r\n", "\n")
    *provenance, schema = vendored.split("\n", PROVENANCE_LINES)

    assert provenance[0].startswith("-- Copied verbatim from procrastinate 3.10.0")
    assert schema == SchemaManager.get_schema().replace("\r\n", "\n"), (
        "The installed procrastinate schema differs from the vendored copy. "
        "Add an Alembic revision with the release's migration SQL and vendor its schema."
    )
