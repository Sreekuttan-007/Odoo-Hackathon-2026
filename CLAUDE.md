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
- `PAYROLL_ENGINE.md` — module layout, core functions, validation matrix
- `PAYRUN_STATE_MACHINE.md` — legal states/transitions, duplicate protection
- `API_PLAN.md` — endpoint inventory by module
- `DEMO_FLOW.md` — the two rehearsed end-to-end demo scenarios + seed data
- `MVP_SCOPE.md` — P0/P1/P2/do-not-build
- `RISKS.md` — risk register and mitigations

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
