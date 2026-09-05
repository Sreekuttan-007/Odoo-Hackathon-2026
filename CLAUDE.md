# PeoplePay360 — HR & Payroll

An integrated HR and Payroll operations platform built for a hackathon.
Employee → Contract → Schedule → Attendance → Time Off → Salary Structure →
Salary Rules → Payrun → Payslip → Validation → Payment → PDF/Email → Dashboard,
as one connected system — not disconnected CRUD pages.

## Current Status

**Phase 0 (Architecture & Rules) is complete.** No application code exists yet.
Do not scaffold the frontend/backend, install packages, create migrations, add
API routes, or build UI components until a human explicitly approves moving to
Phase 1. If asked to "start building," confirm which phase is being started
and check it against the phase plan below first.

Full Phase 0 documentation lives in `docs/`:
- `REQUIREMENTS.md` — problem statement, roles/permission matrix, documented ambiguities
- `DOMAIN_MODEL.md` — core flow, entity descriptions, historical-data rules
- `ARCHITECTURE.md` — stack choice + rationale, layering, folder structure
- `DATABASE_SCHEMA.md` — full entity/field/relationship design
- `CONTRACT_RULES.md` — `getApplicableContract` algorithm and edge cases
- `ATTENDANCE_RULES.md` — worked-hours/exception derivation, corrections
- `LEAVE_RULES.md` — allocation/balance derivation, approval idempotency
- `SALARY_RULE_ENGINE.md` — computation types, sequencing, safe formulas, historical stability
- `PAYROLL_ENGINE.md` — module layout, core functions, validation matrix, Innovation Layer design
- `PAYRUN_STATE_MACHINE.md` — legal states/transitions, duplicate protection
- `API_PLAN.md` — endpoint inventory by module (index; see API_CONTRACT.md for shapes)
- `API_CONTRACT.md` — **the binding frontend/backend contract**: canonical enums, request/response JSON per endpoint, change log
- `DEMO_FLOW.md` — the two rehearsed end-to-end demo scenarios + seed data
- `MVP_SCOPE.md` — P0/P1/P2/do-not-build
- `RISKS.md` — risk register and mitigations

## Parallel Development — Two Agents, One Repo

This project is built by two agents in parallel: **Claude (this agent)** owns
the backend/system-of-truth; **Antigravity** (a separate developer's agent)
owns the frontend. Full protocol below; keep to it on every phase.

**Ownership boundary:**
```
ANTIGRAVITY (frontend/presentation) --HTTP/REST--> CLAUDE (API contracts)
                                                        -> business services -> database
```
- `backend/` is Claude-owned. `frontend/` is Antigravity-owned. `docs/` is
  shared, but Claude owns the business/API documentation within it
  (`API_CONTRACT.md` above all).
- Claude does not redesign or rebuild the frontend. If a frontend change is
  needed, **describe it and stop** — do not silently edit `frontend/` files.
- Frontend mock data is never the source of truth for behavior (a mocked "Net
  Salary = ₹57,000" defines nothing) — the payroll engine, contract
  selection, leave balance, salary rule execution, Payrun state, validation
  warnings, PayTrace, Preflight, and Simulator results all originate from
  backend business logic exclusively.
- Canonical enum names live in `API_CONTRACT.md` §1 — never invent a
  synonym (e.g. `VALIDATED` vs `APPROVED`, `MISSING_CHECKOUT` vs
  `MISSING_CHECK_OUT`); the frontend mirrors these exact strings.

**Before starting backend work in a phase**, identify: which files/dirs will
be touched, whether any are frontend-owned, which API contracts/enums are
affected, and any schema/migration impact. If frontend-owned files need
changes, stop and report the required change instead of making it.

**After finishing backend work in a phase**, report:
1. Backend Changes — what was implemented
2. Files Changed — exact paths
3. Business Rules Added — new behavior
4. API Contract Changes — endpoints added/modified (and the matching
   `API_CONTRACT.md` edit + its change-log row)
5. Frontend Integration Notes — what Antigravity needs to connect
6. New/Changed Enums — canonical values
7. Known Limitations — anything incomplete
8. Tests — what ran, results
9. Next Safe Parallel Task — what Antigravity can do without conflicting

**Recommended stabilization order** (define contract → tell frontend →
replace mock data → integration test, module by module): Employees →
Contracts → Schedules → Attendance → Time Off → Salary Configuration →
Payruns → Payslips → Preflight/PayTrace/Simulator → Dashboard.

## Innovation Layer (Additive to the Original Spec)

Three payroll-intelligence features beyond the base requirements, all
designed to **reuse the real Salary Rule Engine — never a second/fake
calculation path** (see `PAYROLL_ENGINE.md` §Innovation Layer,
`API_CONTRACT.md` §12):

- **PayTrace** — explains how a Payslip's numbers were produced, step by step, reusing the same computation context already built during Compute.
- **Payroll Preflight** — read-only validation run (the same Validation Matrix used by real `Validate`), callable before or after Compute, never mutates state.
- **Payroll Simulator** — previews a hypothetical Salary Rule change via the real rule engine against an in-memory override; never persists to `SalaryRule`, `Payslip`, `Payrun`, or `Contract`.

## Non-Negotiable Invariants

1. Payroll must use the Contract applicable to the payroll period — never a `current_contract` pointer.
2. Conflicting overlapping ACTIVE contracts must never silently pass.
3. Salary Rules determine Payslip values — never a hardcoded net.
4. Salary Rules execute in sequence; later rules may read earlier computed results.
5. Final Payslip totals come from computation only.
6. Approved allocation-based leave reduces balance exactly once.
7. Refused leave never reduces balance.
8. Duplicate Payslips must be detected/prevented at the database level, not just the UI.
9. Dashboard values always come from live database records.
10. Paid/finalized payroll history is not casually editable.

## Development Philosophy

Prioritize correctness, explainability, and demo reliability over feature
count or architectural sophistication. Every business rule must live in a
readable, testable service/domain function — never inside a route handler,
a React component, a database trigger, or a "generic HR engine." No
microservices, no message queues, no unnecessary infra. See `ARCHITECTURE.md`
for the full stack rationale.

Never hardcode payroll results, dashboard metrics, attendance, or leave
balances. If something is incomplete, say so explicitly rather than
simulating it.

## Phase Plan

| Phase | Scope |
|---|---|
| 0 | Architecture + rules (this phase — done) |
| 1 | Foundation: auth, Employee, Departments |
| 2 | Contracts + Working Schedules |
| 3 | Attendance |
| 4 | Time Off + Allocations |
| 5 | Salary Structures + Salary Rules |
| 6 | Payroll Calculation Engine |
| 7 | Payrun + Payslip workflow |
| 8 | Validation + payment lifecycle |
| 9 | Payroll Dashboard |
| 10 | Payslip PDF + email |
| 11 | RBAC hardening + employee-facing views |
| 12 | Seed data + integration testing + demo polish |

Each phase should leave the system in a runnable, demoable state — do not
start a phase whose dependencies (per this table) aren't functionally done.
