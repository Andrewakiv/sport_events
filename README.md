# Sport Events API

Backend service for storing and exposing football and Formula 1 results.

## Current scope

This first increment provides the project skeleton, PostgreSQL connectivity,
health endpoints, Docker development environment, automated tests, CI, and
repository guidance for human and AI contributors.

## Quick start

```bash
cp .env.example .env
docker compose up --build
```

In another terminal, apply the empty Alembic baseline to a fresh database:

```bash
docker compose exec api alembic upgrade head
```

The baseline only records the migration version. Business tables will be added
when their behavior is agreed.

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

Football and Formula 1 modules are intentionally absent. They will be introduced
only after the first business scenario and its acceptance criteria are agreed.
The project avoids placeholder models, repositories, and use cases that do not yet
represent confirmed behavior.

See [docs/agent-workflow.md](docs/agent-workflow.md) for the GitHub workflow.
