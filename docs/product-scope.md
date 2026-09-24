# Product scope

## Agreed direction

- Store and eventually expose football and Formula 1 event schedules and results.
- Start football with the UEFA Champions League. The initial source is football-data.org API v4; the [observed provider contract](champions-league-provider-contract.md) covers four accessible seasons, 2023/24 through 2026/27.
- Include scheduled fixtures as well as finished matches. Do not build live updates in the initial increment; their value, limits, and refresh cost need a separate decision.
- PostgreSQL is the persistent store. Schema changes go through Alembic.
- Jolpica is the intended initial Formula 1 source, but its input contract and persistence design have not been agreed or implemented.

## Implemented today

The repository has FastAPI health endpoints, PostgreSQL connectivity, and an Alembic migration plus ORM models for football competitions, seasons, teams, and matches. It does **not** fetch provider data, populate these tables, expose event queries, or store Formula 1 data. See [ARCHITECTURE.md](../ARCHITECTURE.md) for the exact current components.

## Decisions still to make per issue

Define the import and refresh cadence, event API shape, and Formula 1 data contract when those features are taken up. Reassess live updates separately, including provider entitlement and rate limits. Do not treat the observed four Champions League seasons as an automatically expanding retention policy.
