# CONTRACT RULES — PeoplePay360

## Why This Matters (Invariant 1 & 2)

Payroll must never read "whichever contract is currently on the employee
record." It must resolve the contract that was **legally in force during the
specific payroll period being processed.** This is the single most important
piece of business logic in the system — get it wrong and every payslip built
from that contract is wrong.

## Contract Status Enum

`DRAFT` — not yet in force, excluded from applicability.
`ACTIVE` — currently in force (or was, for a past period still within its dates).
`EXPIRED` — naturally ended (end_date passed, superseded by a new contract).
`TERMINATED` — ended early (employment ended, or contract voided).

Only `ACTIVE` contracts are eligible to be "the applicable contract" for a
period. `EXPIRED`/`TERMINATED` contracts remain queryable for **historical**
periods that fall inside their own date range (a payslip re-run or audit for
a past month must still resolve to the contract that was active *then*, even
though that contract's current status is now `EXPIRED`).

## Algorithm: `getApplicableContract(employee, payrollPeriod)`

```
function getApplicableContract(employee, payrollPeriod):
    # payrollPeriod = { start: date, end: date }

    candidates = Contract.where(
        employee_id = employee.id,
        status IN (ACTIVE, EXPIRED, TERMINATED),   # DRAFT excluded
        start_date <= payrollPeriod.end,
        (end_date IS NULL OR end_date >= payrollPeriod.start)
    )
    # "overlaps" test: contract.start <= period.end AND
    #                   (contract.end IS NULL OR contract.end >= period.start)

    if candidates.count == 0:
        return NO_APPLICABLE_CONTRACT   # -> blocking ERROR at validation

    if candidates.count == 1:
        return candidates[0]

    # More than one contract overlaps the period.
    active_candidates = candidates.filter(status == ACTIVE)

    if active_candidates.count > 1:
        return CONFLICTING_ACTIVE_CONTRACTS   # -> blocking ERROR, must be resolved by HR before payroll can proceed

    if active_candidates.count == 1:
        # one ACTIVE contract plus some EXPIRED/TERMINATED overlap
        # (e.g. mid-period contract change) -> flag for review, still
        # resolvable deterministically by preferring the ACTIVE one,
        # but a WARNING should note a mid-period contract change occurred.
        emit WARNING("Contract changed mid-period")
        return active_candidates[0]

    if active_candidates.count == 0:
        # Only historical (EXPIRED/TERMINATED) contracts overlap — valid for
        # re-running a past period after the contract naturally ended/was
        # terminated. Pick the one whose range best matches the period.
        # If more than one historical contract overlaps (a data problem),
        # this is a CONFLICT and must be flagged, not silently guessed.
        if candidates.count > 1:
            return CONFLICTING_HISTORICAL_CONTRACTS  # -> blocking ERROR
        return candidates[0]
```

This function is pure and testable: given an employee's contract list and a
period, it must always return the same result.

## Overlap Definition

Two date ranges `[a.start, a.end]` and `[b.start, b.end]` (treating `NULL end`
as "infinity") overlap iff `a.start <= b.end AND b.start <= a.end`. This is the
standard interval-overlap test and is what the query above encodes.

## Edge Cases (Must Be Handled, Not Ignored)

| Case | Behavior |
|---|---|
| No contract at all overlaps the period | `NO_APPLICABLE_CONTRACT` — blocking error, employee excluded from payrun (or payslip flagged, not silently skipped) |
| Contract starts *during* the period (new hire mid-month) | Contract is applicable; `worked_days` calculation must prorate from `contract.start_date`, not `period.start` |
| Contract ends *during* the period (termination mid-month) | Contract is applicable; prorate up to `contract.end_date` |
| Two `ACTIVE` contracts overlap the period | `CONFLICTING_ACTIVE_CONTRACTS` — blocking error; must never silently pick one (this is the scenario the spec explicitly calls out: "prevent or clearly flag") |
| A `DRAFT` contract overlaps the period | Ignored entirely — draft contracts are not yet in force |
| Only a `TERMINATED`/`EXPIRED` contract overlaps (re-running a historical period) | Valid and expected; return it |
| Contract's `salary_structure_id` differs from the Payrun's selected structure | `WARNING` — the Payrun's chosen structure wins for calculation (it is what payroll explicitly selected in Step 1), but this mismatch must be surfaced, not silently swallowed |
| Employee has zero contracts ever | Same as "no contract overlaps" — blocking error |

## Non-Goals for MVP

- Automatic contract renewal/generation is out of scope.
- Overlapping *DRAFT* contracts do not need conflict detection (they are not
  in force yet); only `ACTIVE` (and historical) overlaps matter.
