---
name: open-pr
description: Prepare and open a pull request for an existing GitHub issue following this repository's workflow (branch naming, Conventional Commits, PR template, verification evidence). Use when the user asks to commit, push, or open or update a PR.
---

# Open or update a pull request

Follow `AGENTS.md` and `docs/agent-workflow.md`. Ask the user before any
outward-facing action (push, PR creation, comments, board changes).

## Preconditions

- An existing GitHub issue is on the project board with labels. No issue, no PR.
  If missing, stop and tell the user.
- Scope is one issue and one coherent change. Do not include unrelated edits
  (for example someone else's uncommitted changes); stage files explicitly.

## Steps

1. Check state: `git status`, current branch, `gh pr list --head <branch>`.
2. Branch name: `feat/<issue>-<slug>`, `fix/<issue>-<slug>` or
   `chore/<issue>-<slug>`. Branch from up-to-date `origin/main`.
3. Commit with a Conventional Commit message that references the issue, for
   example `fix: improve match card accessibility (#29)`. Never commit secrets,
   `.env`, caches or coverage files.
4. Run the full required checks on the final change set (see `AGENTS.md`):
   backend `uv run --locked ruff check .`, `ruff format --check .`, `mypy`,
   `pytest -m "not integration" --cov` (plus integration tests when touching
   database connections, models, migrations or behavior). When `frontend/` exists and the change touches it, also run the
   `frontend-verify` skill; skip it otherwise.
5. Push, then open the PR (draft unless the user says it is ready):
   `gh pr create --base main --title "<conventional title> (#<issue>)" --body-file <file>`.
   Fill `.github/PULL_REQUEST_TEMPLATE.md`:
   - `Closes #<n>` or `Refs #<n>`
   - acceptance criteria as a checked list
   - verification: verified revision (commit SHA) and concise results
   - database and migration impact, or "None"
   - risks and known limitations, or "None"
6. For updates, edit the PR body so the recorded revision and results match the
   final head commit.
7. Request review with a comment `@codex review` only when the user asks;
   optionally add a narrow focus.

## Merge

Never merge while required CI (`quality`, `integration`, `docker-smoke`, and
`frontend` once that job exists) is failing. Merging is done by a human with GitHub
**Squash and merge** and a Conventional Commit title containing the issue
number, for example `chore: document squash merge policy (#16)`.

## Board

Moving issues between `Ready`, `In Progress`, `In Review` and `Done` needs the
GitHub `project` token scope (`gh auth refresh -s project`). If it is missing,
tell the user instead of guessing.
