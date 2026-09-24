# Agent-assisted GitHub workflow

## Goal

Agents implement and review bounded tasks while GitHub Issues, pull requests,
required CI checks, and human approval remain the source of truth.

## Flow

1. Create an issue with context, acceptance criteria, non-goals, and test expectations.
2. Move the issue to `Ready` when its scope and dependencies are clear, then to `In Progress` while implementing it.
3. Start a dedicated branch for that issue. A new agent task should include the issue or PR link and the desired next action; it does not inherit earlier chat decisions.
4. The agent reads root `AGENTS.md`, the issue or PR (including current comments and checks), and only the relevant linked context documents. It implements the scoped change and runs the checks required by `AGENTS.md`.
5. Open a PR linked to the issue and move the board item to `In Review`. CI runs `quality`, PostgreSQL `integration`, and `docker-smoke` jobs.
6. Request Codex review with `@codex review`; optionally add a narrow focus such as
   `@codex review for database migration safety`.
7. Resolve findings and wait for required CI and human approval. Use GitHub **Squash and merge** with a Conventional Commit title containing the issue number, then move the issue to `Done`.

For a fresh PR-focused chat, provide the PR URL and say whether the agent should review, address review comments, or continue implementation. The PR, linked issue, current repository state, and CI results are the operational context. `ARCHITECTURE.md`, `docs/product-scope.md`, and the provider contract are read only when relevant to that work.

## Repository setup in GitHub

- Protect `main` and require pull requests.
- Require the `quality`, `integration`, and `docker-smoke` CI jobs.
- Require at least one approval and dismissal of stale approvals.
- Disable force pushes and branch deletion for `main`.
- Connect the repository to Codex Cloud and enable Code Review if available.

Creating issues and PRs requires authorized GitHub access. Project status changes
also require access to the project board; repository access alone does not prove
that permission. Repository review rules live in the root `AGENTS.md`.
