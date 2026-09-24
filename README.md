# Sport Events API

Backend service for storing and exposing football and Formula 1 results.

## Current scope

The repository currently provides PostgreSQL connectivity, health endpoints,
Docker development, automated tests and CI, and football persistence models and
migrations. Provider ingestion, event query endpoints, and Formula 1 persistence
are not implemented yet.

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

## Architecture

- `api/routes`: FastAPI route handlers.
- `api/schemas`: Pydantic request and response schemas.
- `database`: SQLAlchemy base and PostgreSQL connection management.
- `settings.py`: environment-based application configuration.

Football ORM models and relationships live in `database/models/football.py`.
There is no football import or read API and no Formula 1 implementation yet.

See [ARCHITECTURE.md](ARCHITECTURE.md) for implemented components,
[docs/product-scope.md](docs/product-scope.md) for agreed scope versus open
decisions, and [docs/agent-workflow.md](docs/agent-workflow.md) for the GitHub
workflow.
