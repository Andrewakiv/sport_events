from importlib.metadata import version
from pathlib import Path

import procrastinate
import pytest
from procrastinate.schema import SchemaManager

VENDORED_SQL = Path("migrations/sql")
BASE_SCHEMA = VENDORED_SQL / "procrastinate_3.10.0_schema.sql"
BASE_VERSION = (3, 10, 0)
PROVENANCE_LINES = 2
PACKAGE_MIGRATIONS = Path(procrastinate.__file__).parent / "sql" / "migrations"


def migration_version(file_name: str) -> tuple[int, int, int]:
    major, minor, patch = file_name[:8].split(".")
    return int(major), int(minor), int(patch)


def read_sql(path: Path) -> str:
    # Line endings depend on the checkout (core.autocrlf), not on the schema.
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


@pytest.mark.skipif(
    version("procrastinate") != "3.10.0",
    reason="revision 0003 keeps the 3.10.0 schema; newer releases are covered by migrations",
)
def test_base_schema_is_a_verbatim_copy_of_procrastinate_3_10_0() -> None:
    *provenance, schema = read_sql(BASE_SCHEMA).split("\n", PROVENANCE_LINES)

    assert provenance[0].startswith("-- Copied verbatim from procrastinate 3.10.0")
    assert schema == SchemaManager.get_schema().replace("\r\n", "\n")


def test_every_newer_procrastinate_migration_is_vendored() -> None:
    newer = sorted(
        path.name
        for path in PACKAGE_MIGRATIONS.glob("*.sql")
        if migration_version(path.name) > BASE_VERSION
    )
    missing = [name for name in newer if not (VENDORED_SQL / name).exists()]

    assert not missing, (
        "The installed procrastinate has schema migrations that no Alembic revision applies. "
        "Copy them into migrations/sql and add revisions that run them (see README, "
        f"'Upgrading procrastinate'), without changing revision 0003: {missing}"
    )
    for name in newer:
        assert read_sql(VENDORED_SQL / name) == read_sql(PACKAGE_MIGRATIONS / name), name
