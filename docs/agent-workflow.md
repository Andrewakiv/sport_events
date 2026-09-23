# Agent-assisted GitHub workflow

## Goal

Agents implement and review bounded tasks while GitHub Issues, pull requests,
required CI checks, and human approval remain the source of truth.

## Flow

1. Create an issue with context, acceptance criteria, non-goals, and test expectations.
2. Move the issue to `Ready` on the project board.
3. Ask an agent to implement only that issue on a dedicated branch.
4. The agent reads `AGENTS.md`, changes code, runs the local checks, and opens a PR.
5. CI runs deterministic linting, formatting, typing, unit, and PostgreSQL integration tests.
6. Request Codex review with `@codex review`; optionally add a narrow focus such as
   `@codex review for database migration safety`.
7. Resolve findings, obtain human approval, merge, and move the issue to `Done`.

## Repository setup in GitHub

- Protect `main` and require pull requests.
- Require the `quality` and `integration` CI jobs.
- Require at least one approval and dismissal of stale approvals.
- Disable force pushes and branch deletion for `main`.
- Connect the repository to Codex Cloud and enable Code Review if available.

GitHub access for creating issues, moving project cards, and opening PRs is handled
through the connected GitHub integration. Repository review behavior is governed by
the `Code Review Rules` section in the root `AGENTS.md`.

