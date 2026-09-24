# Product scope

This document records product decisions, not implementation status. For the
current component overview, see [ARCHITECTURE.md](../ARCHITECTURE.md); verify
implementation details in the code and migrations.

## Agreed direction

- Store and eventually expose football and Formula 1 event schedules and results.
- Start football with the UEFA Champions League. The initial source is football-data.org API v4; the [observed provider contract](champions-league-provider-contract.md) covers four accessible seasons, 2023/24 through 2026/27.
- Include scheduled fixtures as well as finished matches. Do not build live updates in the initial increment; their value, limits, and refresh cost need a separate decision.
- PostgreSQL is the persistent store. Schema changes go through Alembic.
- Jolpica is the intended initial Formula 1 source, but its input contract and persistence design have not been agreed.

## Decisions still to make per issue

Define the import and refresh cadence, event API shape, and Formula 1 data contract when those features are taken up. Reassess live updates separately, including provider entitlement and rate limits. Do not treat the observed four Champions League seasons as an automatically expanding retention policy.
