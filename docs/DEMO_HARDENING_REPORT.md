# Demo Hardening Report (Phase 11)

Feature freeze is in effect after this report. No new product capability was
added in this phase — only correctness/reliability fixes and verification.

**Scope of verification**: this pass was done via automated tests, direct
API calls (`curl`) against the live backend, and code review. There is no
headless browser available in this environment, so the frontend route
sweep, dead-click audit, responsiveness, and accessibility checks (spec
sections 25, 31, 36, 37) were **not** performed via an actual rendered
browser — those items are marked accordingly below rather than claimed as
verified. Everything that could be checked at the API/data level was
checked against the live Neon (Singapore) database, not a mock.

## Environment

- Database: Neon PostgreSQL (Singapore project), confirmed via `SELECT
  current_database(), current_user` → `('neondb', 'neondb_owner')`.
- Alembic: `current` == `heads` == `ea2fc0bd7980`, single head, no
  divergence.
- Backend: FastAPI/uvicorn on `localhost:8000`, `--reload`.
- Frontend: Vite dev server on `localhost:5173`.

## Automated tests

```
cd backend && pytest tests/ -q
```
**200 passed**, 0 failed.

```
cd frontend && npx tsc --noEmit -p . && npm run build
```
Both clean. `npm run lint` → 37 findings, all pre-existing style warnings
(`set-state-in-effect`, `exhaustive-deps`), **0 errors**.

## Fixes made this phase

1. **Stale branding removed** (spec section 46): FastAPI app title/description
   (`backend/app/main.py`) and `docs/DOMAIN_TERMS.md` said "PeoplePay360" —
   changed to "Payloom". Repo-wide grep confirmed these were the only two
   remaining occurrences outside `venv/`.
2. **Canonical demo employee fixed** (spec section 8): no seeded contract
   had exactly the ₹50,000 wage from the spec's mentally-explainable worked
   example. Changed Dave Staff's (`EMP0004`, the `EMPLOYEE`-role login,
   already the demo's clean-payroll subject with attendance and time-off
   context) contract wage from ₹60,000 to ₹50,000 in `seed.py`, applied
   idempotently (re-asserted even on an already-existing contract row, the
   same pattern used for `job_positions.level`). **Verified through the
   real engine, not asserted**: computed a fresh Payrun for Dave and got
   exactly `BASIC 25,000 → HRA 5,000 → ALLOWANCE 2,000 → GROSS 32,000 → PF
   2,500 → NET 29,500` — the spec's canonical numbers, produced by
   `execute_rules()`, not hardcoded. PayTrace on that payslip shows the
   identical breakdown.
3. **Overclaiming pass** (spec section 48): grepped README + all docs for
   "real-time", "fraud detection", "production-ready", "predictive",
   "automated email", "guarantee" — no overclaiming found (one legitimate
   technical use of "guarantee" in `DOMAIN_TERMS.md` describing a verified
   historical-stability property, not marketing language).

## Invariants re-verified live (this session, against Neon)

| Check | Result |
|---|---|
| Neon connectivity + `current`==`heads` | PASS |
| Full backend suite (200 tests) | PASS |
| Frontend `tsc`/`build`/`lint` | PASS (0 errors) |
| No password/hash in any API response | PASS |
| No secrets in built frontend bundle (grepped `dist/assets/*.js` for API keys, DB credentials) | PASS |
| RBAC: EMPLOYEE → Simulator (403) | PASS |
| RBAC: EMPLOYEE → Intelligence brief (403) | PASS |
| RBAC: HR_MANAGER → Intelligence brief (403) | PASS |
| RBAC: EMPLOYEE → own employee list (200) | PASS |
| Idempotency: double Mark Paid on already-PAID Payrun | 409 (correctly rejected) |
| Idempotency: double Validate on already-VALIDATED/PAID Payrun | 409 (correctly rejected) |
| Idempotency: repeated compute doesn't duplicate Payslips | PASS (count stayed 2) |
| Canonical payroll example (₹50,000 wage → ₹29,500 net) | PASS, via real Payrun compute |
| PayTrace shows canonical breakdown correctly | PASS |
| Simulator canonical scenario (HRA 20%→25%, Dave) | PASS — current 29,500 → simulated 30,750, delta 1,250 |
| Simulator non-mutation (rule still 20% after simulating 25%) | PASS |
| AI Intelligence brief with no provider key configured | PASS — `available: false`, `reason: NOT_CONFIGURED`, but still returns a real deterministic summary built from actual evidence (not just a blank error) |
| Payroll status still readable/functional with AI unconfigured | PASS |
| Employee eligibility correctly blocks Payrun creation for a contract-less employee (Eve) at creation time | PASS (`INELIGIBLE_EMPLOYEES`) |

## Not independently re-verified this phase (already covered by existing suite, not re-run live)

- Attendance one-open-session and duplicate check-in rejection — covered
  by `test_attendance_api.py`, part of the 200 passing.
- Time-off exactly-once balance consumption — covered by
  `test_time_off_api.py`'s dedicated balance-math tests.
- Preflight blocker → `409 VALIDATION_BLOCKED` → fix → recheck → succeeds
  — covered by `test_preflight.py`; also manually verified in earlier
  sessions this project (Phase 8/9 completion) against real data, not
  re-run fresh in this pass given time budget.
- PDF generation, PayTrace historical stability under a live rule edit —
  both re-verified live in the Phase 7/8.5/9 sessions against this same
  Neon database; not re-run again this pass since nothing touched that
  code path this phase.

## Explicitly not verified (no browser available in this environment)

- Frontend route sweep / dead-click audit / console zero-tolerance pass
  (spec sections 25, 26, 31) — would require actually rendering the app in
  a browser and clicking through it. `tsc`/`build`/`lint` catch a real
  class of issues (type errors, unreachable imports, obvious lint smells)
  but not runtime-only failures like a broken click handler or a stale
  selected-state bug.
- Responsiveness at 1440/1280/1024px (section 36), accessibility —
  keyboard focus, contrast, reduced-motion (section 37) — same limitation.
- Multi-laptop shared-DB test (section 35) — only one machine's worth of
  API access was available this session.

**Recommendation**: before the actual demo, someone should do one manual
click-through of the Primary E2E Scenario (Employee → Contract → Schedule
→ Attendance/Time Off → Salary Structure → Payrun → Compute → Payslip →
PayTrace → Preflight → Validate → Paid → PDF) and the Innovation Scenario
(PayTrace → Preflight → Simulator → Intelligence) in an actual browser,
watching the console. That's the one category of hardening this pass
could not perform.

## Demo accounts (safe, non-sensitive local/demo credentials)

| Email | Password | Role |
|---|---|---|
| `admin@payloom.local` | `admin123` | ADMIN |
| `hr@payloom.local` | `hr123` | HR_MANAGER |
| `payroll@payloom.local` | `payroll123` | HR_PAYROLL_MANAGER |
| `employee@payloom.local` | `employee123` | EMPLOYEE (Dave Staff — the canonical demo employee) |

## Known limitations (stated truthfully, not fixed this phase)

- No `HR_PAYROLL_USER` demo account exists in `seed.py` — only
  `HR_PAYROLL_MANAGER`. If a judge specifically wants to see the
  read-only-config / operate-only role boundary, that account would need
  to be created manually (`POST /api/admin/users`).
- Employee count (6) is below the spec's suggested 8–15 — sufficient to
  demonstrate every feature (including the deliberate missing-contract
  gap on Eve), but thinner than "representative" headcount.
- No frontend automated test suite exists in this repo — `npm run build` +
  `tsc` + `lint` are the only frontend checks available; there is no
  Jest/Vitest/Playwright suite to run.
- Two Payruns exist for Dave beyond the original seeded/PAID one: the
  original seeded Payrun (Feb 2026, PAID) and a freshly created one (Sept
  2026, left COMPUTED) used to verify the canonical-wage fix through the
  real engine. The Sept 2026 one is intentionally left un-validated so a
  live demo can walk it through Preflight → Validate → Mark Paid as part
  of the presentation rather than showing an already-finished result. The
  HRA 20%→25% scenario used for Simulator verification (Nov 2026) was a
  Simulator call only — nothing was persisted for that period, by design.
