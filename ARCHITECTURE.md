# Current architecture

This document describes what is implemented, not a proposed package layout. The product boundary and open decisions are in [docs/product-scope.md](docs/product-scope.md).

## Request and persistence flow

- `src/sport_events/main.py` creates the FastAPI application, provides the database connection to routes, and closes it on shutdown.
- `src/sport_events/api/routes` contains HTTP handlers; `api/schemas` contains their Pydantic response types. The only routes today are `/api/v1/health/live` and `/api/v1/health/ready`. Liveness does not query PostgreSQL; readiness returns HTTP 503 when the database is unavailable.
- `src/sport_events/database/connection.py` owns the async SQLAlchemy engine and connection check. `database/models/football.py` defines the persisted football records and their ORM relationships.
- `src/sport_events/football_data` contains the isolated football-data.org HTTP client, typed provider responses, and the adapter that creates provider-neutral season snapshots. It fetches one Champions League season at a time using `FOOTBALL_DATA_API_TOKEN`; it does not persist, retry, or schedule imports.
- `src/sport_events/football_sync` contains the plain-Python synchronization operation and records. Its source, lock, and store are injected protocols, so business flow is independent of FastAPI, SQLAlchemy, and provider response types.
- `src/sport_events/database/football_sync.py` implements PostgreSQL advisory locking and atomic upserts. A same-season lock covers fetch through commit, while the write transaction begins only after the provider response has been fully fetched and validated.
- Alembic applies schema changes explicitly. Application startup does not run migrations. The migration history in `migrations/versions` is the source of truth for deployed schema; the models describe the application's ORM mapping.

## Football data already modeled

The current migration creates `football_competitions`, `football_seasons`, `football_teams`, and `football_matches`.

- A season belongs to one competition (`football_seasons.competition_id`); a match belongs to one season (`football_matches.season_id`).
- A match can reference a home and an away team through separate, nullable foreign keys. Its ORM relationships are `home_team` and `away_team`; it also has a `season` relationship. A season has a `competition` relationship.
- Competition, team, and match provider IDs are unique. A season provider ID is unique within its competition. Scores are either both absent or both present and non-negative.

The provider client can be wired to the synchronization operation by the manual `sync-champions-league` command. Synchronization upserts provider-owned fields and never deletes matches missing from a later response. There is no scheduled synchronization, automatic retry, football read API, or Formula 1 schema yet. The observed Champions League input fields and limits are recorded in [the provider contract](docs/champions-league-provider-contract.md), which is not a database schema.

When business rules are added, keep them in plain Python independent of FastAPI, SQLAlchemy, and provider clients. Add a new abstraction only when a concrete behavior needs it.
