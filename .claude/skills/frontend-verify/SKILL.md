---
name: frontend-verify
description: Run the frontend quality checks (lint, format, typecheck, tests with coverage, build) exactly as CI does, on Node 24 in Docker. Use before opening or updating a PR that changes anything under frontend/, or when the local Node version does not satisfy frontend/package.json engines.
---

# Frontend verification

CI runs the `frontend` job on Node 24. Local Node may be older (the Vitest/jsdom
toolchain needs Node >=20.19), so run the checks in a Node 24 container against
a copy of `frontend/`. The container works on a copy and never modifies the
working tree unless you run the optional format step.

## Steps

1. Run from the repository root. Skip the Docker step if `node -v` already
   satisfies `frontend/package.json` `engines`; then run the same npm scripts
   directly in `frontend/`.

```bash
MSYS_NO_PATHCONV=1 docker run --rm -v "$(pwd -W 2>/dev/null || pwd)/frontend:/src:ro" node:24-slim sh -c '
  mkdir /w && cp -r /src/. /w && cd /w && rm -rf node_modules &&
  npm ci --silent &&
  npm audit --audit-level=moderate;
  npm run lint &&
  npm run format:check &&
  npm run typecheck &&
  npm run test:coverage &&
  npm run build'
```

   On PowerShell or Linux/macOS, adapt only the volume path and drop
   `MSYS_NO_PATHCONV`.

2. If `format:check` fails, format inside the same container image and copy
   only the reported files back, then re-run step 1:

```bash
npx prettier --write app
```

3. Report the result: which commands passed, test count, coverage summary, and
   the exact revision (`git rev-parse HEAD` plus whether the tree is dirty).
   Keep passing output short; show full logs only for failures.

## Notes

- Do not install dependencies globally or commit `node_modules`.
- After changing FastAPI response models or routes, run `npm run api:generate`
  in `frontend/` first so `openapi/` and `app/shared/api/schema.d.ts` match.
- Reuse earlier results only while the relevant files are unchanged
  (see `AGENTS.md` verification rules).
