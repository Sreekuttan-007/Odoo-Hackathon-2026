# Payloom — Deployment Guide

Payloom is three pieces that deploy independently:

```
Vite static frontend  ──►  FastAPI backend  ──►  Neon PostgreSQL
   (Vercel / Netlify)       (Render / Railway)     (already set up)
```

The database is already on Neon (`docs/NEON_DEPLOYMENT.md`). This guide covers hosting
the **backend** and the **frontend**. Recommended stack below is all free-tier friendly.

---

## 0. Prerequisites

- The repo is on GitHub (it is: `Sreekuttan-007/Odoo-Hackathon-2026`).
- Your Neon connection string, rewritten to the `postgresql+psycopg://…?sslmode=require` form
  (see `NEON_DEPLOYMENT.md` §1). You'll paste it into the backend host, **not** into the repo.
- An AI key if you want the Payloom Intelligence brief live in production — `GEMINI_API_KEY`
  (or `ANTHROPIC_API_KEY` with `AI_PROVIDER=anthropic`). Optional; the app works without it.

---

## Fast path — Render Blueprint (both services at once)

The repo has a **`render.yaml`** at the root. It creates the backend *and* the
frontend in one go.

1. [dashboard.render.com](https://dashboard.render.com) → **New → Blueprint**.
2. Connect the GitHub repo → Render reads `render.yaml` and shows `payloom-api` + `payloom-web`.
3. Fill the values it prompts for:
   - `payloom-api` → **`DATABASE_URL`**: your Neon `postgresql+psycopg://…?sslmode=require` string
   - `payloom-api` → **`GEMINI_API_KEY`**: your key (or leave blank — the AI brief just falls back)
   - `payloom-web` → **`VITE_API_BASE_URL`**: `https://payloom-api.onrender.com/api`
     (use whatever host Render actually assigns `payloom-api`; keep `/api`)
4. **Apply** → Render builds both. `SECRET_KEY` is auto-generated; `CORS_ORIGINS` defaults to
   `https://payloom-web.onrender.com`.
5. Once `payloom-api` is live → open it → **Shell** → `cd backend && python seed.py` (once).
6. Open `payloom-web`'s URL, log in as `admin@payloom.local` / `admin123`.
7. If login shows a CORS error, set `payloom-api` → `CORS_ORIGINS` to the exact `payloom-web` URL and redeploy.

> Render free static sites don't cold-start; the free web service (backend) sleeps after
> 15 min idle (~30 s wake). For judging, bump `payloom-api` to a paid instance or ping it
> right before.

The manual steps below are the same thing done by hand, or for splitting across Render + Vercel.

---

## 1. Backend → Render (recommended)

[Render](https://render.com) reads a repo, builds it, and gives you an HTTPS URL. Free web
services sleep after 15 min idle (~30 s cold start) — fine for a demo.

### 1a. Create the service

1. Render dashboard → **New → Web Service** → connect the GitHub repo.
2. Settings:
   | Field | Value |
   |---|---|
   | **Root Directory** | `backend` |
   | **Runtime** | Python 3 |
   | **Build Command** | `pip install -r requirements.txt` |
   | **Start Command** | `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
   | **Instance Type** | Free |

### 1b. Environment variables (Render → Environment)

| Key | Value |
|---|---|
| `DATABASE_URL` | your `postgresql+psycopg://…?sslmode=require` Neon string |
| `SECRET_KEY` | a long random string — `python -c "import secrets;print(secrets.token_urlsafe(48))"` |
| `APP_ENV` | `production` |
| `CORS_ORIGINS` | your frontend URL, e.g. `https://payloom.vercel.app` (add more, comma-separated, no trailing slash) |
| `AI_PROVIDER` | `gemini` (or `anthropic`) — optional |
| `GEMINI_API_KEY` | your key — optional |

> The backend reads config from real environment variables when no `.env` file is present
> (`app/core/config.py`), so the Render dashboard values are all it needs.

### 1c. First deploy

- Render builds, runs `alembic upgrade head` (creates every table on Neon), then starts uvicorn.
- **Seed once** (Render → your service → **Shell**):
  ```bash
  cd backend && python seed.py
  ```
  Idempotent — safe to re-run. Creates the demo accounts + demo Payrun.
- Verify: open `https://<your-backend>.onrender.com/api/health` → `{"status":"ok"}`.
  Then `https://<your-backend>.onrender.com/docs` for the API explorer.

### Alternative: Railway / Fly.io
Same idea. Railway: set Root Directory `backend`, add the same env vars, start command
`alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT`. Fly.io needs a
`fly.toml` + `Dockerfile` — more work; only pick it if you already use Fly.

---

## 2. Frontend → Vercel (recommended)

1. [Vercel](https://vercel.com) → **Add New → Project** → import the same GitHub repo.
2. Settings:
   | Field | Value |
   |---|---|
   | **Root Directory** | `frontend` |
   | **Framework Preset** | Vite |
   | **Build Command** | `npm run build` (default) |
   | **Output Directory** | `dist` (default) |
3. Environment Variables:
   | Key | Value |
   |---|---|
   | `VITE_API_BASE_URL` | `https://<your-backend>.onrender.com/api` (note the `/api` suffix) |
4. Deploy. Vercel gives you `https://<project>.vercel.app`.

### SPA routing
Payloom uses client-side routing (`react-router`). Vercel's Vite preset handles the
history-API fallback automatically. If you use **Netlify** instead, add
`frontend/public/_redirects` with:
```
/*    /index.html   200
```
(Cloudflare Pages / Render Static Sites: set the SPA / "rewrite all to index.html" option.)

---

## 3. Wire the two together

1. Deploy the backend first, note its URL.
2. Set the frontend's `VITE_API_BASE_URL` to `<backend-url>/api` and deploy the frontend.
3. Go back to the backend host and set `CORS_ORIGINS` to the frontend's URL. Redeploy the backend.
4. Open the frontend, log in as `admin@payloom.local` / `admin123`.

If login fails with a CORS error in the browser console, `CORS_ORIGINS` on the backend
doesn't exactly match the frontend origin (scheme + host, no trailing slash, no path).

---

## 4. Post-deploy checklist

- [ ] `GET <backend>/api/health` → `{"status":"ok"}`
- [ ] `POST <backend>/api/auth/login` with a demo account returns a token
- [ ] Frontend loads, login works, dashboard shows real numbers
- [ ] Open a computed Payrun → Preflight renders → **Generate Payroll Brief** works
      (or shows the deterministic fallback if no AI key / quota hit — that's fine)
- [ ] Open a Payslip → PayTrace → PDF downloads
- [ ] Neon cold start: first request after ~5 min idle takes ~6 s, then fast
- [ ] `alembic current` == `alembic heads` (run in the backend host shell)

---

## 5. Production hardening (beyond a demo)

Not required for the hackathon, but real deployments should:

- Rotate `SECRET_KEY` and never commit it; rotate the Neon password and any AI key that
  was ever pasted into a chat or log.
- Restrict `CORS_ORIGINS` to exactly the production frontend origin (no `*`).
- Put the backend behind the host's HTTPS (Render/Railway do this automatically).
- Set `APP_ENV=production` so the global error handler stops returning exception detail
  in responses (`app/main.py`).
- Add a paid instance if you can't tolerate cold starts during judging.
- Consider a read-only Neon branch for demos so a live edit can't corrupt the seed data.

---

## 6. Environment variable reference

**Backend** (`backend/app/core/config.py`):

| Var | Required | Default | Notes |
|---|---|---|---|
| `DATABASE_URL` | yes (prod) | `sqlite:///./payloom.db` | Neon: `postgresql+psycopg://…?sslmode=require` |
| `SECRET_KEY` | yes (prod) | dev placeholder | JWT signing — must be secret + stable |
| `CORS_ORIGINS` | yes (prod) | localhost:5173 | comma-separated frontend origins |
| `APP_ENV` | no | `development` | set `production` to hide error detail |
| `AI_PROVIDER` | no | `gemini` | `gemini` \| `anthropic` |
| `GEMINI_API_KEY` | no | — | enables the AI brief when `AI_PROVIDER=gemini` |
| `ANTHROPIC_API_KEY` | no | — | enables the AI brief when `AI_PROVIDER=anthropic` |

**Frontend** (`frontend/src/services/api.ts`):

| Var | Required | Default | Notes |
|---|---|---|---|
| `VITE_API_BASE_URL` | yes when deployed separately | `http://localhost:8000/api` | must include `/api`; baked in at build time |
