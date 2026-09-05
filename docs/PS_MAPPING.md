# Payloom — Problem-Statement Mapping (Phase 12)

Maps each expected HR/payroll capability to what's actually built. Status is honest:
**DONE** = implemented + tested; **PARTIAL** = built with a stated boundary; **NOT BUILT** = deliberately out of scope.

| # | Requirement | Implementation | Route (UI) | Backend / API | Demo step | Status |
|---|---|---|---|---|---|---|
| 1 | **Authentication** | JWT (HS256) login, `/auth/me`, bcrypt password hashing | `/login` | `POST /api/auth/login`, `GET /api/auth/me` | (login before demo) | **DONE** |
| 2 | **Roles / access control** | 5 roles; backend dependencies per route (`get_current_payroll_operator` etc.); frontend route guards | all protected routes | every non-public route | Q&A only (accounts ready) | **DONE** |
| 3 | **User management** | Admin creates / deactivates users, assigns roles | `/admin/users` | `GET/POST/PATCH /api/admin/users` | Q&A only | **DONE** |
| 4 | **Employee management** | Kanban + list + detail; create/edit; Department, Job Position, Manager, Working Schedule relations | `/employees`, `/employees/:id` | `GET/POST/PATCH /api/employees` | 0:55 — open Dave Staff | **DONE** |
| 5 | **Departments** | Minimal CRUD + reusable selector + seed data | `/departments` | `GET/POST /api/departments` | shown inline on employee | **DONE** |
| 6 | **Job Positions** | Minimal CRUD + reusable selector; hierarchy validation | (inline selector) | `GET/POST /api/job-positions` | shown inline | **DONE** |
| 7 | **Contracts** | Historical, date-bound; wage (money-safe `Decimal`); salary structure link; overlap prevention; period-applicability resolver | `/contracts`, `/contracts/:id`, `?employee_id=` | `GET/POST/PATCH /api/contracts` | 1:05 — Dave + Aarav contracts | **DONE** |
| 8 | **Working Schedules** | Weekly pattern lines (start/end/break); derived daily + weekly hours | `/working-schedules`, `/working-schedules/new`, `/:id` | `GET/POST/PATCH /api/working-schedules` | referenced at 1:20 | **DONE** |
| 9 | **Attendance** | Global + employee-filtered list; detail; Check In / Check Out widget with live elapsed; HR corrections; derived worked-hours / overtime; one-session-per-day + overlap protection | `/attendance`, `/attendance/:id`, `?employee_id=` | `GET/POST/PATCH /api/attendance` | 1:20 — Dave's attendance | **DONE** |
| 10 | **Time Off — Types** | Config: unit (DAYS/HOURS), requires-allocation, approval policy, active, display color | `/time-off/types`, `/:id` | `GET/POST/PATCH /api/time-off/types` | Q&A / brief mention | **DONE** |
| 11 | **Time Off — Allocations** | Allocated / Taken / Remaining; approve/refuse; **derived** balance (never persisted) | `/time-off/allocations`, `/:id`, `?employee_id=` | `GET/POST/PATCH /api/time-off/allocations` | Q&A | **DONE** |
| 12 | **Time Off — Requests** | Create, approve, refuse; balance breakdown; exactly-once consumption (double-approve can't double-deduct) | `/time-off/requests`, `/:id`, `?employee_id=` | `GET/POST/PATCH /api/time-off/requests`, balance-preview endpoint | 1:30 — Dave's leave | **DONE** |
| 13 | **Salary Structures** | Ordered Salary Rules; active/inactive; code | `/payroll/salary-structures`, `/:id` | `GET/POST/PATCH /api/payroll/structures` | 1:40 — Regular Salary | **DONE** |
| 14 | **Salary Rules** | FIXED / PERCENTAGE / FORMULA; categories BASIC/ALLOWANCE/GROSS/DEDUCTION/NET; sequence ordering; constrained AST evaluator (no `eval`) | `/payroll/salary-rules` | `GET/POST/PATCH /api/payroll/rules` | 1:40 — rule list | **DONE** |
| 15 | **Payrun — two-step creation** | Step 1 scope (structure + period); Continue previews backend-eligible employees and persists **nothing**; Step 2 explicit selection creates DRAFT | `/payroll/payruns/new` | `GET /api/payroll/payruns/eligible-employees`, `POST /api/payroll/payruns` | 2:05 — wizard | **DONE** |
| 16 | **Payrun lifecycle** | DRAFT → COMPUTED → VALIDATED → PAID state machine; invalid transitions rejected (`409`) | `/payroll/payruns/:id` | `POST .../compute`, `.../validate`, `.../mark-paid` | 2:20, 3:10, 4:25 | **DONE** |
| 17 | **Payslips** | Real computation; rule-by-rule PayslipLine trace; per-payslip warnings; historically-stable snapshots | `/payroll/payslips`, `/:id` | `GET /api/payroll/payslips`, `/:id` | 2:30 | **DONE** |
| 18 | **Payroll calculation engine** | Deterministic; sequence-ordered rule execution; `Decimal` + `ROUND_HALF_UP`; category totals = sum of lines; canonical example verified (₹50k → ₹29,500) | — | `app/services/payroll_engine.py` | 2:20 compute | **DONE** |
| 19 | **Validation / warnings** | Preflight readiness engine (13 checks, BLOCKER/WARNING/INFO, evidence + resolution); **server-side validation gate** recomputes + re-runs Preflight, aborts `409 VALIDATION_BLOCKED` on any blocker | `/payroll/payruns/:id` (Preflight panel) | `GET/POST .../preflight`; gate inside `.../validate` | 2:55 — Preflight | **DONE** |
| 20 | **Payment status / history** | PAID state + `paid_at` / `paid_by`; per-payslip status; Payrun list shows history | `/payroll/payruns`, `/payroll/payslips` | `POST .../mark-paid`, list endpoints | 4:25 | **DONE** |
| 21 | **Payslip PDF** | ReportLab, generated from persisted computed data (never recomputed) | button on Payslip detail | `GET /api/payroll/payslips/:id/pdf` | 4:40 | **DONE** |
| 22 | **Dashboard** | Operational overview derived live from real records (employees, contracts, attendance, pending time off) | `/dashboard` | reuses list endpoints | 0:30 | **DONE** |
| 23 | **Bulk payslip email / "Send Payslips"** | — | — | — | — | **NOT BUILT** — no email provider configured; not faked |
| 24 | **PayTrace (explainability)** | Deterministic per-Payslip calculation explainer rebuilt from PayslipLine snapshots; historically stable under later rule edits | `/payroll/payslips/:id/trace` | `GET /api/payroll/payslips/:id/trace` | 2:30 | **DONE** (beyond PS) |
| 25 | **Preflight (readiness)** | See #19 | `/payroll/payruns/:id` | `.../preflight` | 2:55 | **DONE** (beyond PS) |
| 26 | **Payroll Simulator (what-if)** | Deterministic overrides through the **same** engine; transient rules never persisted; per-employee + company impact; annualized estimate | `/payroll/simulator` | `POST /api/payroll/simulator/run` | 3:25 | **DONE** (beyond PS) |
| 27 | **Payloom Intelligence (AI brief)** | Grounded AI brief over sanitized evidence + source registry; every claim validated; deterministic fallback; provider-optional | Payrun detail → "Generate Payroll Brief" | `POST /api/payroll/payruns/:id/intelligence/brief` | 3:55 | **DONE** (beyond PS) |
| 28 | **AI plain-language payslip explanation** | "Explain in Simple Language" over the verified PayTrace; hallucinated rule codes filtered out | `/payroll/payslips/:id/trace` | `GET .../trace/explain` | 2:50 (optional) | **DONE** (beyond PS) |
| 29 | **Mid-period contract proration** | — | — | — | Q&A | **NOT BUILT** — engine applies the full structure; Preflight raises INFO |
| 30 | **Attendance/leave → automatic salary adjustment** | Context only — exposed to rule formulas, not auto-applied | — | context in `payroll_engine` | Q&A | **PARTIAL** — deliberate; extensible via a rule |
| 31 | **Statutory tax / compliance engine** | — | — | — | Q&A | **NOT BUILT** — PF/PT rules are configurable examples, not compliance |

---

## Coverage summary

- **Core HR + payroll PS requirements (#1–22, 24):** DONE, except bulk payslip email (#23, deliberately not built — no provider).
- **Innovation layer (#24–28):** DONE — this is where Payloom goes beyond a standard HRMS.
- **Explicit non-scope (#23, 29, 31):** stated as limitations, not hidden.
- **Partial by design (#30):** attendance/leave are payroll context; a Salary Rule can consume them, but there's no hardcoded deduction.
