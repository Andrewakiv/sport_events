# Sport Events API

Backend service for storing and exposing football and Formula 1 results.

## Current scope

The repository currently provides PostgreSQL connectivity, health endpoints,
Docker development, automated tests and CI, football persistence models and
migrations, an isolated football-data.org client, and an idempotent Champions
League season synchronization operation, and a read-only Champions League match
API. Formula 1 persistence is not implemented yet.

## Quick start

```bash
docker compose up --build
```

The Docker Compose setup supplies database configuration directly; a local
`.env` file is not required for this path. In another terminal, apply the
Alembic migrations to a fresh database:

```bash
docker compose exec api alembic upgrade head
```

The migrations create the football competition, season, team, and match tables.

Open:

- API docs: <http://localhost:8000/docs>
- Liveness: <http://localhost:8000/api/v1/health/live>
- Readiness: <http://localhost:8000/api/v1/health/ready>

## Local quality checks

```bash
uv sync --locked
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked mypy
uv run --locked pytest -m "not integration" --cov
```

`uv sync` creates and manages the local `.venv` automatically. Use `uv add`
for runtime dependencies and `uv add --dev` for development dependencies, then
commit both `pyproject.toml` and `uv.lock`.

Integration tests require PostgreSQL and `SPORT_EVENTS_TEST_DATABASE_URL`.

The football-data.org client reads `FOOTBALL_DATA_API_TOKEN` from the local
environment or `.env`. The token is only needed when calling that client; the
API and tests do not call the provider automatically. Never commit a real token.

After applying migrations, synchronize one selected season manually with its
start year:

```bash
uv run --locked sync-champions-league 2026
```

The command validates the complete provider response before its single database
write transaction. Imports of the same season cannot overlap, repeated imports
update existing records, and provider omissions do not delete stored matches.

## Champions League read API

- `GET /api/v1/football/champions-league/matches` lists imported matches.
- `GET /api/v1/football/champions-league/matches/{match_id}` returns one imported
  match, or HTTP 404 if it is not stored in the Champions League competition.

Optional list filters are combined: `season` is the season's start year,
`date` is a UTC calendar date (`YYYY-MM-DD`), `team_id` matches either home or
away team, and `status` matches the exact stored provider status. Public match,
season, and team IDs are provider IDs, not database primary keys.

Results are ordered by kickoff ascending, then match ID ascending. Pagination
uses `limit` (default 50, range 1–100) and `offset` (default 0, non-negative).
The response includes `items`, filtered `total`, `limit`, and `offset`; an empty
page is HTTP 200. Invalid query parameters return HTTP 422.

Each match exposes its season dates, kickoff, stored status and stage, matchday,
group, nullable teams, and nullable score (`home`, `away`, `duration`). Missing
scores remain `null`, not fabricated zeroes. Reads never call the provider or
trigger synchronization. Offset pages can change when an import updates data.

## Architecture

- `api/routes`: FastAPI route handlers.
- `api/schemas`: Pydantic request and response schemas.
- `database`: SQLAlchemy base and PostgreSQL connection management.
- `football_data`: Champions League provider HTTP client and response types.
- `football_sync`: provider- and database-independent synchronization records and operation.
- `football_read`: plain-Python match views, query records, and reader protocol.
- `settings.py`: environment-based application configuration.

Football ORM models and relationships live in `database/models/football.py`.
`database/football_read.py` implements the read queries. There is no scheduled
import or Formula 1 implementation yet.

See [ARCHITECTURE.md](ARCHITECTURE.md) for implemented components,
[docs/product-scope.md](docs/product-scope.md) for agreed scope versus open
decisions, and [docs/agent-workflow.md](docs/agent-workflow.md) for the GitHub
workflow.
