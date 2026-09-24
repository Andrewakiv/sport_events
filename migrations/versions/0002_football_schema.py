"""Add football competition, season, team, and match tables.

Revision ID: 0002_football_schema
Revises: 0001_baseline
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_football_schema"
down_revision: str | None = "0001_baseline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "football_competitions",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("provider_id", sa.Integer(), nullable=False, unique=True),
        sa.Column("code", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
    )
    op.create_table(
        "football_seasons",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column(
            "competition_id",
            sa.BigInteger(),
            sa.ForeignKey("football_competitions.id"),
            nullable=False,
        ),
        sa.Column("provider_id", sa.Integer(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.UniqueConstraint("competition_id", "provider_id", name="uq_football_seasons_provider"),
    )
    op.create_table(
        "football_teams",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("provider_id", sa.Integer(), nullable=False, unique=True),
        sa.Column("name", sa.String(length=150), nullable=False),
    )
    op.create_table(
        "football_matches",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("provider_id", sa.Integer(), nullable=False, unique=True),
        sa.Column(
            "season_id", sa.BigInteger(), sa.ForeignKey("football_seasons.id"), nullable=False
        ),
        sa.Column("home_team_id", sa.BigInteger(), sa.ForeignKey("football_teams.id")),
        sa.Column("away_team_id", sa.BigInteger(), sa.ForeignKey("football_teams.id")),
        sa.Column("kickoff_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("stage", sa.String(length=40), nullable=False),
        sa.Column("matchday", sa.Integer()),
        sa.Column("group_name", sa.String(length=50)),
        sa.Column("home_score", sa.Integer()),
        sa.Column("away_score", sa.Integer()),
        sa.Column("score_duration", sa.String(length=30)),
        sa.CheckConstraint(
            "(home_score IS NULL AND away_score IS NULL) "
            "OR (home_score IS NOT NULL AND away_score IS NOT NULL)",
            name="ck_football_matches_complete_score",
        ),
        sa.CheckConstraint(
            "home_score >= 0 AND away_score >= 0",
            name="ck_football_matches_score_nonnegative",
        ),
    )


def downgrade() -> None:
    op.drop_table("football_matches")
    op.drop_table("football_teams")
    op.drop_table("football_seasons")
    op.drop_table("football_competitions")
