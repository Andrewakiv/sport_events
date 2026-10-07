# Current architecture

This document describes what is implemented, not a proposed package layout. The product boundary and open decisions are in [docs/product-scope.md](docs/product-scope.md).

## Request and persistence flow

- `src/sport_events/main.py` creates the FastAPI application, configures the database, and closes the database engine on shutdown. `api/dependencies.py` injects the database session and match queries and owns request-scoped read-session cleanup; routers do not construct persistence adapters.
- `src/sport_events/api/routes` contains HTTP handlers; `api/schemas` contains health response types. Health routes are `/api/v1/health/live` and `/api/v1/health/ready`. Liveness does not query PostgreSQL; readiness returns HTTP 503 when the database is unavailable. Champions League list and detail routes under `/api/v1/football/champions-league/matches` read imported records without contacting the provider.
- `src/sport_events/database/connection.py` owns the async SQLAlchemy engine, connection check, and read-session creation. Sessions use the database's default isolation without overrides; their transaction ends when the request dependency closes the session. `database/models/football.py` defines the persisted football records and their ORM relationships.
- `src/sport_events/football_data` contains the isolated football-data.org HTTP client, typed provider responses, and the adapter that creates provider-neutral season snapshots. It fetches one Champions League season at a time using `FOOTBALL_DATA_API_TOKEN`; it does not persist, retry, or schedule imports.
- `src/sport_events/football_sync` contains the plain-Python synchronization operation and records. Its source, lock, and store are injected protocols, so business flow is independent of FastAPI, SQLAlchemy, and provider response types.
- `src/sport_events/database/football_sync.py` implements PostgreSQL advisory locking and atomic upserts. A same-season lock covers fetch through commit, while the write transaction begins only after the provider response has been fully fetched and validated.
- `src/sport_events/football_models.py` holds the single set of Pydantic filters and response models shared by the football endpoints and queries. `queries/champions_league_matches.py` implements `ChampionsLeagueMatchQueries`: it builds and executes competition-scoped SQL using an injected `AsyncSession` and projects database columns directly into response models, without intermediate dataclasses or mapping factories. Explicit joins, filters, deterministic ordering, and bounded pagination preserve the public contract documented in [README.md](README.md#champions-league-read-api). Count and page are read in one SQL statement, sharing one snapshot under PostgreSQL's default `READ COMMITTED`; a left join preserves the total even when the page is empty. It does not create, commit, or close sessions. This read/serialization layer shares Pydantic models intentionally; synchronization business flow remains independent.
- Alembic applies schema changes explicitly. Application startup does not run migrations. The migration history in `migrations/versions` is the source of truth for deployed schema; the models describe the application's ORM mapping.

## Football data already modeled

The current migration creates `football_competitions`, `football_seasons`, `football_teams`, and `football_matches`.

- A season belongs to one competition (`football_seasons.competition_id`); a match belongs to one season (`football_matches.season_id`).
- A match can reference a home and an away team through separate, nullable foreign keys. Its ORM relationships are `home_team` and `away_team`; it also has a `season` relationship. A season has a `competition` relationship.
- Competition, team, and match provider IDs are unique. A season provider ID is unique within its competition. Scores are either both absent or both present and non-negative.

The provider client can be wired to the synchronization operation by the manual `sync-champions-league` command. Synchronization upserts provider-owned fields and never deletes matches missing from a later response. There is no scheduled synchronization, automatic retry, Formula 1 client, or Formula 1 schema yet. The observed Champions League and Formula 1 input fields and limits are recorded in their [football](docs/champions-league-provider-contract.md) and [Jolpica](docs/jolpica-f1-provider-contract.md) provider contracts, which are not database schemas.

When business rules are added, keep them in plain Python independent of FastAPI, SQLAlchemy, and provider clients. Add a new abstraction only when a concrete behavior needs it.
