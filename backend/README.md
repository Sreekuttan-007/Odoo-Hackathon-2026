# PeoplePay360 — Backend

Node.js + TypeScript + Express + Prisma + PostgreSQL, per `docs/ARCHITECTURE.md`.
Phase 1 scope only: foundation, auth, RBAC skeleton, Employee/Department/Job
Position CRUD. No payroll logic exists yet — see `docs/MVP_SCOPE.md` and the
repo-root `CLAUDE.md` phase plan.

## Setup

```bash
cd backend
npm install
cp .env.example .env
cp .env.test.example .env.test
docker compose up -d          # starts Postgres (dev db + test db)
npx prisma migrate dev        # creates schema + Phase 1 tables
npx prisma db seed            # loads deterministic demo data
```

## Run

```bash
npm run dev        # ts-node-dev, auto-reload, reads .env
npm run build && npm start   # compiled production run
```

Health check: `GET http://localhost:4000/api/health` → `{ "status": "ok" }`

## Test

```bash
npm test
```

This resets the **test** database (`.env.test`'s `DATABASE_URL`, a separate
database from dev) via `prisma migrate reset --force`, re-seeds it, then runs
the Jest + Supertest suite against a live instance of the app. Never run
against a database you care about — it is dropped and recreated every run.

## Demo Users

All demo users share the password `Password123!` (seeded in
`prisma/seed.ts`, development only):

| Email | Role |
|---|---|
| employee@example.com | EMPLOYEE |
| hr@example.com | HR_MANAGER |
| payroll@example.com | HR_PAYROLL_USER |
| payrollmanager@example.com | HR_PAYROLL_MANAGER |
| admin@example.com | ADMIN |

## Environment Variables

See `.env.example`. `APP_ENV`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `CORS_ORIGINS`,
and `PORT` have safe development defaults; `DATABASE_URL` and `SECRET_KEY`
are required and the app fails to start without them (`src/config/env.ts`).

## API Contract

The binding contract with the frontend agent is `../docs/API_CONTRACT.md`.
Phase 1 implements: `POST/GET /api/auth/*`, `GET /api/health`,
`/api/employees`, `/api/departments`, `/api/job-positions`. Everything else
in that document remains planning-only until its phase lands.

## Known Limitations (Phase 1)

- No hard-delete endpoints for Employee/Department/Job Position — deactivate
  via `PATCH` (`status`/`isActive`), consistent with `DATABASE_SCHEMA.md`'s
  archival policy.
- Job position's department is not cross-validated against the employee's own
  department (Phase 1 spec §28 leaves this optional; not enforced).
- No `/api/users` admin endpoints yet (not in Phase 1 scope).
