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

- Frontend: <http://localhost:3000/football/champions-league/matches>
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

### Scheduled and manual synchronization

Imports run in a separate `sync-worker` process backed by a
[procrastinate](https://procrastinate.readthedocs.io/) job queue stored in the same
PostgreSQL database (migrations `0003` and `0004`). The worker needs
`FOOTBALL_DATA_API_TOKEN`; Docker Compose passes your local `.env` to it.

- **Schedule.** Set `SPORT_EVENTS_CHAMPIONS_LEAGUE_SYNC_SEASON` to the current
  season's start year. The worker queues that season on
  `SPORT_EVENTS_CHAMPIONS_LEAGUE_SYNC_CRON` (UTC, default every 6 hours). Without
  the setting nothing is scheduled; completed seasons are never polled.
- **Manual run or backfill.** Queue any season for the worker:

  ```bash
  uv run --locked sync-champions-league 2026          # local worker
  docker compose run --rm api sync-champions-league 2026
  ```

  Start a local worker with
  `uv run --locked procrastinate --app=sport_events.sync_jobs.app.app worker --queues=football`.
- **Retries.** Timeouts, network errors, provider 429/5xx, and database outages are
  retried up to `SPORT_EVENTS_CHAMPIONS_LEAGUE_SYNC_MAX_ATTEMPTS` (default 3) with
  exponential backoff (30 s, capped at 300 s). A missing or rejected token and
  invalid provider data fail immediately.
- **Outcomes.** Every run is recorded in `football_sync_runs`: season, trigger,
  start/end time, status, attempts, created/updated match counts, and a safe
  failure reason. A run left `doing` by a dead worker is detected within about
  five minutes, recorded, and retried while attempts remain; otherwise it stays
  `interrupted`. Queue it again to retry.

  ```sql
  SELECT season_start_year, trigger, status, attempts, matches_created,
         matches_updated, failure_reason, started_at, finished_at
  FROM football_sync_runs ORDER BY started_at DESC LIMIT 20;
  ```

Each attempt validates the complete provider response before its single database
write transaction. Only one run per season can wait in the queue or execute at a
time, repeated imports update existing records, and provider omissions do not
delete stored matches. Refresh the frontend after a successful import. An empty
database shows an empty match list. API errors show an error state.

### Stopping the sync worker

`docker compose stop sync-worker` sends SIGTERM. The worker stops taking jobs and
stops scheduling, then gives a running attempt 45 seconds
(`--shutdown-graceful-timeout`) to finish. An attempt still running is cancelled:
its season transaction rolls back, the journal records `worker shut down during the
attempt`, and the run is queued again while attempts remain. Docker's
`stop_grace_period` (60 s) leaves room for this before SIGKILL; a killed worker's
run is picked up by the recovery job instead.

### Upgrading procrastinate

Migration `0003` keeps the procrastinate 3.10.0 schema and must not change.
Procrastinate ships later schema changes as SQL files named
`<version>_<serial>_<pre|post>_<name>.sql`; `pre` scripts must run before the new
code is deployed and `post` scripts after it
([procrastinate docs](https://procrastinate.readthedocs.io/en/stable/howto/production/migrations.html)).
`tests/unit/test_vendored_queue_schema.py` fails while an installed release has
scripts that no revision applies.

1. Copy the new scripts from the installed package's `procrastinate/sql/migrations`
   into `migrations/sql` unchanged, and add an Alembic revision that executes them
   in file order the same way `0003` does.
2. Stop the worker and do not run `sync-champions-league` until the upgrade is done
   (the API does not queue jobs):

   ```bash
   docker compose build api sync-worker            # images with the new code and revisions
   docker compose stop sync-worker
   docker compose run --rm api alembic upgrade head
   docker compose up -d api sync-worker
   ```

Upgrading without stopping the worker requires separate `pre` and `post` revisions
deployed one procrastinate release at a time, as the procrastinate docs describe.

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
trigger synchronization. Each list response reads its count and items from one
database snapshot. Offset pages can still change between requests when an import
updates data.

## Frontend development

The React and TypeScript frontend lives in `frontend/`. It uses the existing
FastAPI OpenAPI document for generated request and response types. With the API
running on port 8000 and Node.js 24 (the CI/Docker version) installed:

```bash
cd frontend
npm ci
npm run dev
```

Open <http://localhost:5173/football/champions-league/matches>. The dev server
proxies `/api` to FastAPI on port 8000; the Docker frontend uses nginx for the
same path. Every displayed match comes from the backend database.

Frontend checks are:

```bash
npm run lint
npm run format:check
npm run typecheck
npm run test:coverage
npm run build
```

`npm run lint` generates React Router route types before typed ESLint checks,
so it also works on a fresh checkout without a prior dev-server or build run.

After changing FastAPI response models or routes, regenerate the committed API
schema and TypeScript declarations with `npm run api:generate` from `frontend/`.

## Architecture

- `api/routes`: FastAPI route handlers.
- `api/schemas`: Pydantic request and response schemas.
- `api/dependencies.py`: request-scoped read sessions and injected dependencies.
- `database`: SQLAlchemy base and PostgreSQL connection management.
- `football_data`: Champions League provider HTTP client and response types.
- `football_sync`: provider- and database-independent synchronization records, operation,
  and run/retry rules.
- `sync_jobs`: procrastinate queue, scheduled and recovery jobs, and failure classification.
- `football_models.py`: shared Pydantic filters and response models, without duplicate read DTOs.
- `queries`: match queries using caller-owned sessions, returning the shared response models.
- `settings.py`: environment-based application configuration.
- `frontend`: React Router SPA for browsing Champions League schedules and results.

Football ORM models and relationships live in `database/models/football.py`.
`queries/champions_league_matches.py` implements the read queries. There is no
Formula 1 implementation yet.

See [ARCHITECTURE.md](ARCHITECTURE.md) for implemented components,
[docs/product-scope.md](docs/product-scope.md) for agreed scope versus open
decisions, and [docs/agent-workflow.md](docs/agent-workflow.md) for the GitHub
workflow.
