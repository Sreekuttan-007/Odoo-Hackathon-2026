# PAYRUN STATE MACHINE — PeoplePay360

## States

`DRAFT -> COMPUTED -> VALIDATED -> PAID`, plus `CANCELLED` reachable from
`DRAFT` or `COMPUTED` (not from `VALIDATED`/`PAID` — cancelling finalized
payroll is not a simple status flip, see MARK PAID doc note below).

## Creation (Two-Step, 0.20)

- **Step 1 (scope)**: user picks Salary Structure + payroll period. "Continue"
  does **not** persist a Payrun row — it is a client-side (or a transient
  server-side draft-not-yet-committed) step only.
- **Step 2 (employee selection)**: server computes and returns eligible
  employees (`getEligibleEmployees()` — active employees with an applicable
  contract overlapping the period, per CONTRACT_RULES.md). User explicitly
  selects a subset.
- **"Create Payrun"** is the single moment a `Payrun` row is inserted, with
  status `DRAFT`, and (in the same transaction) one `Payslip` row per selected
  employee is pre-created in a `DRAFT` sub-state — or, alternative design:
  Payslips are only created at Compute time and Payrun creation just persists
  the chosen employee-id list. **Chosen approach:** Payslip rows are created
  at Compute time, not at Payrun creation, so a `DRAFT` Payrun with no
  Payslips yet is a valid, inspectable state (simpler mental model — "Payslip
  exists" always means "has been computed at least once").

## Transition Table

| From | Action | To | Guard |
|---|---|---|---|
| (none) | Create Payrun (Step 2 submit) | DRAFT | at least 1 employee selected |
| DRAFT | Compute | COMPUTED | for each selected employee: applicable contract resolvable (else per-employee ERROR warning, employee excluded or payrun blocked per policy — see PAYROLL_ENGINE.md validation matrix) |
| COMPUTED | Compute (re-run) | COMPUTED | **idempotent**: existing Payslips for this Payrun are recomputed in place (delete-and-recreate their PayslipLines, or update), never duplicated — see Duplicate Protection below |
| COMPUTED | Validate | VALIDATED | zero blocking ERROR-severity warnings remain across all Payslips |
| VALIDATED | Mark Paid | PAID | all Payslips have required bank details (or a documented override); this is the last mutation the state machine allows |
| DRAFT or COMPUTED | Cancel | CANCELLED | terminal; only allowed before validation |
| VALIDATED | Send Payslips | VALIDATED (no state change) | delivery is orthogonal to the state machine — see 0.30 |
| PAID | Send Payslips | PAID (no state change) | payslips can be (re)emailed after payment |

## Forbidden Transitions (Explicit)

- `DRAFT -> VALIDATED` (must Compute first — cannot validate an uncomputed Payrun, 0.22).
- `DRAFT -> PAID`, `COMPUTED -> PAID` (must Validate first — cannot mark paid before validation, 0.22).
- `VALIDATED -> DRAFT`, `PAID -> *` (no backward transitions once validated; "paid/finalized payroll history must remain historically trustworthy," 0.28/Invariant 10).
- `PAID -> CANCELLED` (finalized payroll is not casually cancellable; a correction requires an explicit, separate reversal workflow — out of scope for MVP, documented as a known gap).

Any attempted forbidden transition returns an explicit error naming the
current state and the requested action — never a silent no-op and never a
best-effort partial transition.

## Duplicate Protection Across Repeated Compute (0.22, test #16)

`Compute` must be safe to click twice:

```
function computePayrun(payrunId):
    payrun = Payrun.find(payrunId)
    assert payrun.status in (DRAFT, COMPUTED)   # guard: cannot compute a VALIDATED/PAID/CANCELLED payrun

    for employee in payrun.selectedEmployees:
        existingPayslip = Payslip.find(payrun_id = payrun.id, employee_id = employee.id)
        contract = getApplicableContract(employee, payrun.period)
        if contract is an error condition:
            record PayrollWarning(ERROR, ...); continue
        lines = computePayslipLines(structure, contract, context)
        if existingPayslip:
            replace existingPayslip's PayslipLines with `lines` (in a transaction)
        else:
            create Payslip + PayslipLines
    payrun.status = COMPUTED
```

Because the lookup keys on the unique `(employee_id, payrun_id)` constraint
(DATABASE_SCHEMA.md), a second Compute call **updates** the existing Payslip
rather than inserting a duplicate — satisfying both 0.22 ("repeated Compute
actions [must not] generate duplicate Payslips") and 0.26 (duplicate payslip
protection is a real DB constraint, not just a frontend check).

## Payslip-Level Status

Each Payslip mirrors a subset of the Payrun's lifecycle
(`DRAFT/COMPUTED/VALIDATED/PAID/CANCELLED`) so that an individual
employee's payslip can carry its own blocking warnings without blocking
the entire batch from being inspected — but **Validate** and **Mark Paid**
at the Payrun level are documented (Phase 6+ decision) to require ALL
member Payslips to individually clear validation before the Payrun as a
whole advances, rather than silently skipping problem employees.
