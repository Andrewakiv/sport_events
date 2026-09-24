## Summary

<!-- What changed and why? -->

Closes #

## Acceptance criteria

- [ ]

## Verification

- [ ] `uv run --locked ruff check .`
- [ ] `uv run --locked ruff format --check .`
- [ ] `uv run --locked mypy`
- [ ] `uv run --locked pytest -m "not integration" --cov`
- [ ] `uv run --locked pytest -m integration` when changing database connections, models, migrations, or behavior

## Database and operational impact

<!-- Migrations, rollout concerns, compatibility, or "None". -->

## Risks

<!-- Known risks or "None". -->
