# CLAUDE.md

Prediction market analytics platform: Next.js frontend (`frontend/`), FastAPI backend (`backend/`), PostgreSQL, hourly Polymarket ingestion via APScheduler, auth via Clerk. See README.md for the full architecture.

## Git workflow

- Never commit directly to `main`. The only exception is the repository's first commit.
- Do all work on a branch named `feature/<name>`, e.g. `feature/watchlists`.
- Make small commits, each covering one change, with a clear message saying what changed (and why, when it isn't obvious).
- Before every commit, run the tests and make sure they pass:
  ```sh
  docker compose run --rm web pytest
  ```
  If any test fails, don't commit: fix the problem or report the failure.
- Ask before running `git push`, every time. Approval for one push doesn't cover the next.
- `main` deploys automatically (Vercel for the frontend), so anything merged into `main` goes live.

## Destructive commands

Before running any command that deletes things, explain what it will delete and whether that can be undone, then wait for confirmation. This includes:

- `docker compose down -v`: removes the containers **and the named volumes**, including the PostgreSQL data. All ingested market history and user watchlists are lost for good.
- `docker system prune` (and `-a`, `--volumes`): removes stopped containers, unused networks, dangling or unused images, build cache and, with `--volumes`, unused volumes, including those of other projects on this machine.
- `rm`, `git clean`, `git reset --hard`, `git branch -D` and similar.
- Alembic downgrades (`alembic downgrade ...`) and any SQL that drops or truncates tables or deletes rows.

## Secrets

- Never put secrets (passwords, API keys, tokens, `CLERK_SECRET_KEY`, real `DATABASE_URL` credentials) in any file that gets committed.
- Pass secrets in through environment variables or uncommitted env files: `backend/.env` and `frontend/.env.local`. Make sure both are listed in `.gitignore` (and `.dockerignore`).
- Only variables prefixed `NEXT_PUBLIC_` reach the browser. Never give a secret that prefix.
- Configuration that isn't secret (e.g. `INGESTION_INTERVAL_MINUTES`, `NEXT_PUBLIC_API_URL`) can have defaults in committed example files such as `.env.example`.

## Database

- Change the schema only through Alembic migrations in `backend/alembic/`; never edit tables by hand. Commit each migration with the model change it belongs to.
- Keep `Market` (current metadata) and `MarketSnapshot` (one row per hourly run) as separate tables. Snapshots are append-only history.

## Backend conventions

- The backend is a long-running process because APScheduler runs inside it. Don't restructure it for serverless.
- Ingestion must stay fault tolerant: log each run and catch errors so a bad Polymarket response never crashes the scheduler.
- Tests must not call the real Polymarket API or Clerk. Mock external HTTP calls.
- Public endpoints (`/health`, `/markets/...`) need no auth. Every `/watchlists` endpoint requires a verified Clerk JWT, and users may only read or change their own watchlists.

## Frontend conventions

- Prefer Server Components for data reads; avoid client-side `useEffect` fetching unless the page needs interactivity.
