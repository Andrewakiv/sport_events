# Repository instructions

## Working agreement

- Keep changes scoped to one issue and one coherent pull request.
- Before editing, read the nearest `AGENTS.md` that applies to the target files.
- Do not commit secrets, generated caches, local environment files, or credentials.
- Do not introduce a production dependency without explaining the need in the PR.
- Prefer explicit, typed code over framework magic.
- Use `uv` for dependency management, commit `uv.lock`, and do not install project dependencies with `pip` directly.

## Project context

- For changes to component boundaries or data flow, consult `ARCHITECTURE.md`.
- For feature decisions, consult `docs/product-scope.md`. For Champions League provider work, also consult `docs/champions-league-provider-contract.md`.
- For issue, board, review, and merge steps, consult `docs/agent-workflow.md`.
- Read the issue or pull request and its current comments and checks for task-specific state. Use only the documents relevant to that task; previous chat history is not a source of truth.

## Architecture

- Introduce files and abstractions only when they are required by agreed behavior.
- When business logic is introduced, keep it independent of FastAPI, SQLAlchemy, and external APIs.
- Prefer names that describe a concrete responsibility; avoid generic catch-all names.

## Verification

- Add or update tests for every behavior change.
- Use two verification stages:
  1. During implementation, run only tests relevant to the changed behavior and targeted checks as needed. Do not rerun the full suite after every small edit.
  2. Before opening or updating a PR, run the full required checks on the final change set: `uv run --locked ruff check .`, `uv run --locked ruff format --check .`, `uv run --locked mypy`, and `uv run --locked pytest -m "not integration" --cov`. Also run integration tests when changing database connections, models, migrations, or behavior.
- Reuse successful verification results while the files and configuration relevant to those checks remain unchanged. Repeat affected checks after further changes; rerun the full suite when shared behavior, dependencies, test configuration, or the impact of a change makes targeted verification insufficient. Do not reuse results from an unverified final change set.
- Record the verified revision or change set and test results in the PR. Keep successful command output concise; inspect detailed logs when a check fails.

## Database changes

- Use Alembic for schema changes; never mutate production schema from application startup.
- Make migrations forward-safe and call out destructive or locking operations in the PR.
- Do not rewrite an applied migration; add a new migration.

## Git and pull requests

- Before implementation, ensure an existing GitHub Issue is on the project board with relevant labels; no issue means no PR.
- Use branches named `feat/<issue>-<slug>`, `fix/<issue>-<slug>`, or `chore/<issue>-<slug>`.
- Use Conventional Commits.
- Link every PR to its issue with `Closes #<number>` or `Refs #<number>` in the description, and include acceptance criteria, test evidence, migration impact, and risks.
- Never merge while required CI checks are failing.
- After required CI passes and a human approves, use GitHub **Squash and merge** for every PR; do not use merge commits or rebase merges.
- Give the squash commit a Conventional Commit title with the issue number, for example `chore: document squash merge policy (#16)`.
- Do not rewrite existing `main` history to retrofit this policy.

## Code Review Rules

### Architecture boundaries

- Flag business rules that import FastAPI, SQLAlchemy, or provider SDKs.
  Safe path: keep business rules in plain Python and inject explicitly named dependencies.

### Database safety

- Flag destructive migrations, table rewrites, or unbounded data migrations without an explicit rollout plan.
  Safe path: use additive, reversible steps and describe operational impact in the PR.
