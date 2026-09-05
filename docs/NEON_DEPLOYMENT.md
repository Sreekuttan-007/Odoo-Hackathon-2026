# Neon Deployment (Phase 8.5)

Moving Payloom's database from local Docker PostgreSQL to [Neon](https://neon.tech)
(cloud PostgreSQL) for demo/deployment purposes. This is a **hosting change,
not a technology change** — Neon is PostgreSQL, so the backend's stack
(SQLAlchemy, Alembic, `psycopg[binary]`) is unchanged. Local Docker
PostgreSQL keeps working exactly as before; Neon is an alternative
`DATABASE_URL`, not a replacement.

## 1. Create the Neon project

1. Sign in at [console.neon.tech](https://console.neon.tech) and create a project.
2. Open **Connection Details** and copy the connection string. Neon gives
   you something like:
   ```
   postgresql://<user>:<password>@<host>/<database>?sslmode=require
   ```
3. Payloom uses SQLAlchemy with the `psycopg` (v3) driver, so rewrite the
   scheme from `postgresql://` to `postgresql+psycopg://` — everything
   else (host, user, password, database, `?sslmode=require`) stays as
   Neon gave it to you:
   ```
   postgresql+psycopg://<user>:<password>@<host>/<database>?sslmode=require
   ```

## 2. Set `DATABASE_URL`

Open your local `.env` (repo root, gitignored — **never** paste this into
a chat message, commit, or log) and replace the `DATABASE_URL` line with
the rewritten Neon string from step 1. Leave everything else in `.env` as
it is. See `.env.example` for the exact format with placeholders.

## 3. Apply migrations

From `backend/`, with your venv active:

```bash
alembic upgrade head
alembic current   # should match `alembic heads` — one head, no divergence
```

This creates every table/enum via the existing migration chain — nothing
is created by `Base.metadata.create_all()` in this flow, and nothing here
touches your local Docker database.

## 4. Seed demo data

```bash
python seed.py
```

`seed.py` is idempotent — every row is looked up by a stable business key
(employee code, work email, salary-rule code, etc.) before being created,
so running it again is always safe and never produces duplicates. It's
been verified to produce byte-identical row counts across repeated runs
against the local dev database.

Demo accounts it creates (`role` / `password`):
- `admin@payloom.local` / `admin123` — ADMIN
- `hr@payloom.local` / `hr123` — HR_MANAGER
- `payroll@payloom.local` / `payroll123` — HR_PAYROLL_MANAGER
- `employee@payloom.local` / `employee123` — EMPLOYEE

These are intentionally non-sensitive local/demo credentials, safe to
document. Don't reuse them for anything real.

The seed also computes one demo Payrun (Aarav Mehta + Dave Staff, Regular
Salary structure, Feb 2026) so PayTrace and Preflight have real historical
data to show immediately, and deliberately leaves one employee (Eve
Unlinked) without a Contract — that's the "missing contract" Preflight
scenario, not a bug.

## 5. Start the backend against Neon

```bash
uvicorn app.main:app --reload
```

Hit `GET /api/health` — should return `{"status": "ok"}`. This confirms
the app boots with the Neon `DATABASE_URL`; it doesn't itself prove
Neon connectivity (the health check doesn't touch the DB) — the real
proof is any endpoint that queries the database, e.g. logging in.

## 6. Point the frontend at your backend (only if deployed separately)

If frontend and backend run on the same machine (e.g. local dev against
a Neon-backed backend), no frontend change is needed — it still talks to
`http://localhost:8000/api` by default. If you deploy the frontend
separately from the backend, set (in `frontend/.env`, also gitignored):

```env
VITE_API_BASE_URL=https://your-deployed-backend.example.com/api
```

And make sure that backend's `CORS_ORIGINS` includes the deployed
frontend's origin.

## Troubleshooting

**SSL error on connect** — confirm the connection string ends in
`?sslmode=require` (Neon requires SSL; don't strip it or disable SSL
globally to work around an error).

**Driver / URL scheme error** — confirm the scheme is
`postgresql+psycopg://`, not bare `postgresql://` or `postgresql+psycopg2://`.
This project uses psycopg v3 (`psycopg[binary]` in `requirements.txt`),
not psycopg2.

**`alembic current` doesn't match `alembic heads`** — stop and investigate
rather than running `alembic stamp` to force them to match. Stamping
hides a real divergence instead of fixing it. Report what each command
actually printed.

**Connection works locally but times out from a deployed host** — check
that host's outbound network policy; Neon itself doesn't restrict by
source IP on the standard connection string.

**Stale/dropped connections after idling** — the engine already sets
`pool_pre_ping=True` (`backend/app/db/database.py`), which discards a
dead pooled connection and transparently reconnects rather than failing
the request. If you still see intermittent failures, that's worth
reporting rather than silently retrying.

## Safety notes

- Migrations are the only thing allowed to change schema. Nothing in
  this app calls `Base.metadata.create_all()` against `DATABASE_URL` at
  runtime — that only happens inside the pytest fixtures, which use a
  separate, hardcoded `sqlite:///:memory:` engine (`backend/tests/conftest.py`)
  and never read `DATABASE_URL` at all. Running the test suite can never
  touch Neon, by construction — not because of an environment-variable
  guard, but because the test engine is a different, hardcoded database.
- `seed.py` never drops or truncates anything — every write is a
  look-up-then-create, and it's meant to be safe to run against a demo
  database repeatedly.
- Nothing in this repo logs `DATABASE_URL`. If you add logging, mask
  credentials before printing a connection string.
