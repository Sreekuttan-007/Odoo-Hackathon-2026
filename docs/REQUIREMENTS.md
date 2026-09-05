# REQUIREMENTS — PeoplePay360

## A. Problem Understanding (Plain English)

PeoplePay360 is a connected HR + Payroll system. An HR/Payroll team needs to:
hire an employee, define their working schedule and pay terms (contract), track
whether they actually show up and work (attendance), let them take leave against
an entitlement (time off), and — at the end of a period — turn all of that into a
correct paycheck (payslip), built from a chain of configurable salary rules, with
a review/warning stage before money is considered "paid."

**Why this is not "just CRUD":** every module feeds the next one's math.

- The Payslip is not a form you fill in — it is *computed* from a Contract, a
  Salary Structure, and a chain of Salary Rules run in sequence, using
  attendance/leave as inputs to worked-days.
- The Contract used for a payslip is not "whatever is on the employee record
  today" — it must be the contract that was legally in force during that
  specific payroll period, which requires an actual date-overlap algorithm and
  conflict detection.
- Leave balances are not a stored number — they are derived from
  allocation − approved consumption, and that consumption must happen exactly
  once, exactly on approval.
- A Payrun is not a single-step "submit" button — it has a two-step scope→selection
  creation flow and a state machine (DRAFT → COMPUTED → VALIDATED → PAID) with
  guarded transitions and duplicate protection.
- The Dashboard is not a static set of numbers — every metric must be
  aggregated from the real records produced by the modules above.

A system that lets any of these shortcuts happen (hardcoded net pay, a
`current_contract` pointer instead of period-based selection, double-deducted
leave, duplicate payslips, a dashboard fed by mock data) is not a correct HR/Payroll
system, regardless of how complete its UI looks. Correctness of the chain is the
actual deliverable.

## B. Non-Functional Priorities (Hackathon Context)

1. **Demo reliability > feature count.** A smaller, fully-wired system beats a
   large partially-working one.
2. **Explainability.** Every business rule must be traceable to a specific,
   readable function — no rule should live only inside a UI component or a
   opaque generic "engine."
3. **Determinism.** Same inputs (contract, attendance, salary rules) must always
   produce the same payslip. No randomness, no silent fallbacks.
4. **Minimal dependencies.** Prefer a few well-understood libraries over a large
   dependency tree.
5. **Backend-enforced authorization.** Frontend hiding of buttons is UX only;
   every mutating endpoint re-checks role permissions server-side.

## C. Roles (Restated) and Permission Matrix

Five roles: `EMPLOYEE`, `HR_MANAGER`, `HR_PAYROLL_USER`, `HR_PAYROLL_MANAGER`, `ADMIN`.

Legend: **C**reate, **R**ead, **U**pdate, **D**elete, **A**pprove/Process, **—** none.

| Module / Action                         | Employee | HR Manager | HR Payroll User | HR Payroll Manager | Admin |
|------------------------------------------|:---:|:---:|:---:|:---:|:---:|
| Own profile, attendance, leave, payslip (read) | R | R | R | R | R |
| Employee records (CRUD)                  | — | CRUD | CRUD (inherits HR Mgr) | CRUD (inherits) | CRUD |
| Own Attendance (create check-in/out)     | C | CRUD | CRUD | CRUD | CRUD |
| Attendance corrections (any employee)    | — | U | U | U | U |
| Contracts                                | — | CRUD | CRUD | CRUD | CRUD |
| Working Schedules                        | — | CRUD | CRUD | CRUD | CRUD |
| Time Off Requests — own                  | C, R | R | R | R | R |
| Time Off Requests — approve/refuse       | — | A | A | A | A |
| Time Off Allocations                     | — | CRUD | CRUD | CRUD | CRUD |
| Time Off Types                           | — | CRUD | CRUD | CRUD | CRUD |
| Salary Structures                        | — | — | R only | CRUD | CRUD |
| Salary Rules                             | — | — | R only | CRUD | CRUD |
| Payruns (create/compute/validate/pay)    | — | — | CRUD + process | CRUD + process | CRUD + process |
| Payslips (read/update status)            | R (own) | — | R, U | CRUD | CRUD |
| Payroll Dashboard                        | — | — (not specified; excluded from HR Manager per spec) | R | R | R |
| User / Role management                   | — | — | — | — | CRUD |

Note: the spec explicitly states HR Manager "cannot access payroll administration."
Whether HR Manager sees the Payroll Dashboard is not specified — **assumption:**
Dashboard is gated behind payroll roles (`HR_PAYROLL_USER`+) and Admin, since its
metrics are payroll-derived. Document, do not implement.

Authorization must be enforced in the service layer (see `ARCHITECTURE.md`), not
only in route middleware or the frontend router.

## D. Ambiguities Identified (Documented, Not Resolved by Implementation)

| # | Ambiguity | Simplest Assumption |
|---|-----------|----------------------|
| 1 | Exact Contract status enum names | `DRAFT`, `ACTIVE`, `EXPIRED`, `TERMINATED` (see CONTRACT_RULES.md) |
| 2 | Exact Payrun/Payslip status enum names | `DRAFT`, `COMPUTED`, `VALIDATED`, `PAID`, `CANCELLED` |
| 3 | Whether HR Manager sees the Dashboard | Excluded (payroll-derived data); revisit with judges/spec owner |
| 4 | Formula salary rule expression language | Constrained whitelist expression evaluator (no `eval`), see SALARY_RULE_ENGINE.md |
| 5 | Overtime pay computation | Out of scope for MVP; attendance records "Overtime" as a status/flag only, not paid automatically |
| 6 | Multi-currency / statutory tax compliance | Explicitly out of scope (see MVP_SCOPE.md `DO NOT BUILD`) |
| 7 | Whether Employee record requires a linked User account 1:1 | Assumption: Employee has an optional `user_id` FK; not every Employee necessarily logs in (e.g. seed data), but any Employee who logs in maps to exactly one User |
| 8 | Half-day / hourly leave granularity | Supported at the `unit` level (DAYS or HOURS) per Time Off Type; no partial-day-with-DAYS-unit splitting in MVP |
| 9 | Working schedule overlap handling (e.g. split shifts) | Not supported in MVP; one contiguous line per day, validated for start < end and non-negative break |

Any implementation choice beyond these documented assumptions must be flagged
before being written into Phase 1+ code.
