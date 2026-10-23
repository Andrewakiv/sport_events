"""Add the journal of queued football synchronization runs.

Revision ID: 0004_football_sync_runs
Revises: 0003_procrastinate_schema
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_football_sync_runs"
down_revision: str | None = "0003_procrastinate_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "football_sync_runs",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("job_id", sa.BigInteger(), nullable=False, unique=True),
        sa.Column("season_start_year", sa.Integer(), nullable=False),
        sa.Column("trigger", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("matches_created", sa.Integer(), nullable=True),
        sa.Column("matches_updated", sa.Integer(), nullable=True),
        sa.Column("failure_reason", sa.String(length=200), nullable=True),
        sa.CheckConstraint(
            "trigger IN ('scheduled', 'manual')", name="ck_football_sync_runs_trigger"
        ),
        sa.CheckConstraint(
            "status IN ('running', 'retry_scheduled', 'succeeded', 'failed', "
            "'skipped_locked', 'interrupted')",
            name="ck_football_sync_runs_status",
        ),
        sa.CheckConstraint("attempts >= 1", name="ck_football_sync_runs_attempts"),
        sa.CheckConstraint(
            "matches_created >= 0 AND matches_updated >= 0",
            name="ck_football_sync_runs_counts_nonnegative",
        ),
    )
    op.create_index(
        "ix_football_sync_runs_season_started",
        "football_sync_runs",
        ["season_start_year", "started_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_football_sync_runs_season_started", table_name="football_sync_runs")
    op.drop_table("football_sync_runs")
