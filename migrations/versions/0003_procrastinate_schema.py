"""Install the procrastinate job queue schema.

The SQL is vendored from procrastinate 3.10.0 so this revision stays the same when the
package is upgraded. A procrastinate upgrade that changes its schema needs a new revision
applying that release's migration SQL.

Revision ID: 0003_procrastinate_schema
Revises: 0002_football_schema
"""

from collections.abc import Sequence
from pathlib import Path

from alembic import context, op
from sqlalchemy.util import await_only

revision: str = "0003_procrastinate_schema"
down_revision: str | None = "0002_football_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA_SQL = Path(__file__).parent.parent / "sql" / "procrastinate_3.10.0_schema.sql"

DROP_SCHEMA_SQL = """
DROP TABLE IF EXISTS
    procrastinate_events,
    procrastinate_periodic_defers,
    procrastinate_jobs,
    procrastinate_workers
CASCADE;
DROP FUNCTION IF EXISTS
    procrastinate_defer_jobs_v1,
    procrastinate_defer_periodic_job_v2,
    procrastinate_fetch_job_v2,
    procrastinate_finish_job_v1,
    procrastinate_cancel_job_v1,
    procrastinate_retry_job_v1,
    procrastinate_retry_job_v2,
    procrastinate_notify_queue_job_inserted_v1,
    procrastinate_notify_queue_abort_job_v1,
    procrastinate_trigger_function_status_events_insert_v1,
    procrastinate_trigger_function_status_events_update_v1,
    procrastinate_trigger_function_scheduled_events_v1,
    procrastinate_trigger_abort_requested_events_procedure_v1,
    procrastinate_unlink_periodic_defers_v1,
    procrastinate_register_worker_v1,
    procrastinate_unregister_worker_v1,
    procrastinate_update_heartbeat_v1,
    procrastinate_prune_stalled_workers_v1;
DROP TYPE IF EXISTS
    procrastinate_job_to_defer_v1,
    procrastinate_job_event_type,
    procrastinate_job_status;
"""


def upgrade() -> None:
    _execute_script(SCHEMA_SQL.read_text(encoding="utf-8"))


def downgrade() -> None:
    _execute_script(DROP_SCHEMA_SQL)


def _execute_script(sql: str) -> None:
    if context.is_offline_mode():
        op.execute(sql)
        return
    # asyncpg prepares statements, which rejects multi-statement scripts; its plain
    # execute() uses the simple query protocol on the migration's own connection.
    driver_connection = op.get_bind().connection.driver_connection
    if driver_connection is None:
        raise RuntimeError("the migration connection has no driver connection")
    await_only(driver_connection.execute(sql))
