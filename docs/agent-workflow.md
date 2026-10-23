# Agent-assisted GitHub workflow

## Goal

Agents implement and review bounded tasks while GitHub Issues, pull requests,
required CI checks, and human approval remain the source of truth.

## Flow

1. Create an issue with context, acceptance criteria, non-goals, and test expectations.
2. Move the issue to `Ready` when its scope and dependencies are clear, then to `In Progress` while implementing it.
3. Start a dedicated branch for that issue from a clean checkout (see [Starting from a checkout that is not clean](#starting-from-a-checkout-that-is-not-clean)). A new agent task should include the issue or PR link and the desired next action; it does not inherit earlier chat decisions.
4. The agent reads root `AGENTS.md`, the issue or PR (including current comments and checks), and only the relevant linked context documents. It implements the scoped change and runs the checks required by `AGENTS.md`.
5. Open a PR linked to the issue and move the board item to `In Review`. CI runs `quality`, PostgreSQL `integration`, and `docker-smoke` jobs.
6. Request Codex review with `@codex review`; optionally add a narrow focus such as
   `@codex review for database migration safety`.
7. Resolve findings and wait for required CI and human approval. Use GitHub **Squash and merge** with a Conventional Commit title containing the issue number, then move the issue to `Done`.

For a fresh PR-focused chat, provide the PR URL and say whether the agent should review, address review comments, or continue implementation. The PR, linked issue, current repository state, and CI results are the operational context. `ARCHITECTURE.md`, `docs/product-scope.md`, and the provider contract are read only when relevant to that work.

## Starting from a checkout that is not clean

Uncommitted work belongs to the issue it was made for. Finish it before starting
another issue instead of working around it.

1. Run `git status` and note the current branch. Ignored files (dependencies,
   build output, coverage) do not count.
2. If there are uncommitted or untracked changes, stop and report to the user
   which branch and files they are on.
3. Agree how to finish them:
   - commit them to their own issue branch with a Conventional Commit message,
     run the required checks, and push or update that issue's PR when the user
     asks; or
   - the user explicitly discards them or defers them, for example as a local
     WIP commit on that issue's branch.
4. Only then switch to up-to-date `origin/main` and create the new issue branch
   in the existing checkout.

Do not switch branches with the changes carried along, stash them, or create git
worktrees or repository copies unless the user asks for it.

## Repository setup in GitHub

- Protect `main` and require pull requests.
- Require the `quality`, `integration`, and `docker-smoke` CI jobs.
- Require at least one approval and dismissal of stale approvals.
- Disable force pushes and branch deletion for `main`.
- Connect the repository to Codex Cloud and enable Code Review if available.

Creating issues and PRs requires authorized GitHub access. Project status changes
also require access to the project board; repository access alone does not prove
that permission. Repository review rules live in the root `AGENTS.md`.
