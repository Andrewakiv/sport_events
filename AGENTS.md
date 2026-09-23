# Repository instructions

## Working agreement

- Keep changes scoped to one issue and one coherent pull request.
- Before editing, read the nearest `AGENTS.md` that applies to the target files.
- Do not commit secrets, generated caches, local environment files, or credentials.
- Do not introduce a production dependency without explaining the need in the PR.
- Prefer explicit, typed code over framework magic.
- Use `uv` for dependency management, commit `uv.lock`, and do not install project dependencies with `pip` directly.

## Architecture

- Introduce files and abstractions only when they are required by agreed behavior.
- When business logic is introduced, keep it independent of FastAPI, SQLAlchemy, and external APIs.
- Prefer names that describe a concrete responsibility; avoid generic catch-all names.

## Verification

- Run `uv run --locked ruff check .` and `uv run --locked ruff format --check .`.
- Run `uv run --locked mypy`.
- Run `uv run --locked pytest -m "not integration" --cov` for every change.
- Run integration tests when changing database connections, models, migrations, or behavior.
- Add or update tests for every behavior change.

## Database changes

- Use Alembic for schema changes; never mutate production schema from application startup.
- Make migrations forward-safe and call out destructive or locking operations in the PR.
- Do not rewrite an applied migration; add a new migration.

## Git and pull requests

- Use branches named `feat/<issue>-<slug>`, `fix/<issue>-<slug>`, or `chore/<issue>-<slug>`.
- Use Conventional Commits.
- Include the linked issue, acceptance criteria, test evidence, migration impact, and risks in the PR.
- Never merge while required CI checks are failing.

## Code Review Rules

### Architecture boundaries

- Flag business rules that import FastAPI, SQLAlchemy, or provider SDKs.
  Safe path: keep business rules in plain Python and inject explicitly named dependencies.

### Database safety

- Flag destructive migrations, table rewrites, or unbounded data migrations without an explicit rollout plan.
  Safe path: use additive, reversible steps and describe operational impact in the PR.
