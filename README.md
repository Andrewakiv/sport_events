# Sport Events API

Backend service for storing and exposing football and Formula 1 results.

## Current scope

The repository currently provides PostgreSQL connectivity, health endpoints,
Docker development, automated tests and CI, football persistence models and
migrations, an isolated football-data.org client, and an idempotent Champions
League season synchronization operation. Event query endpoints and Formula 1
persistence are not implemented yet.

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

## Architecture

- `api/routes`: FastAPI route handlers.
- `api/schemas`: Pydantic request and response schemas.
- `database`: SQLAlchemy base and PostgreSQL connection management.
- `football_data`: Champions League provider HTTP client and response types.
- `football_sync`: provider- and database-independent synchronization records and operation.
- `settings.py`: environment-based application configuration.

Football ORM models and relationships live in `database/models/football.py`.
There is no scheduled import, football read API, or Formula 1 implementation yet.

See [ARCHITECTURE.md](ARCHITECTURE.md) for implemented components,
[docs/product-scope.md](docs/product-scope.md) for agreed scope versus open
decisions, and [docs/agent-workflow.md](docs/agent-workflow.md) for the GitHub
workflow.
