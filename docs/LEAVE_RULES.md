# LEAVE RULES — PeoplePay360

## Balance Algorithm

For an employee + TimeOffType where `requires_allocation = true`:

```
allocated = SUM(TimeOffAllocation.allocated_amount
                WHERE employee_id, time_off_type_id, status = APPROVED,
                      validity window covers the relevant date)

taken = SUM(TimeOffRequest.duration
            WHERE employee_id, time_off_type_id, status = APPROVED)

remaining = allocated - taken
```

Nothing here is stored independently — `taken` and `remaining` are always
computed at read time from the two source tables. This guarantees they can
never drift out of sync with the underlying approved records (0.14).

For a TimeOffType where `requires_allocation = false`, no balance check is
performed; requests can be approved without a balance ceiling (e.g. unpaid
leave, sick leave with no cap — policy detail left to seed data).

## Request Lifecycle (State Machine)

```
        create
(none) --------> PENDING
                    |
        approve     |     refuse
        v----------------------v
    APPROVED               REFUSED
```

`CANCELLED` is an additional state an employee can move a `PENDING` request
into (withdraw before decision); once `APPROVED` or `REFUSED`, a request is
final for MVP (no un-approve workflow — a correction requires HR creating an
explicit adjustment, out of scope for MVP).

## Approval / Refusal Behavior (Invariants 6 & 7)

- **Before approval**: if `requires_allocation`, validate
  `duration <= remaining` (computed as above, excluding the request being
  decided). If insufficient, approval is rejected with a blocking error —
  HR cannot force-approve past the balance in MVP (a documented
  simplification; could be relaxed to a warning-only override later).
- **On approval**: the request's status flips to `APPROVED`. Because `taken`
  is *derived* from approved requests (not manually decremented), the balance
  update is automatic and atomic with the status change — there is no
  separate "deduct balance" step that could be skipped or double-run.
- **On refusal**: status flips to `REFUSED`. Since only `APPROVED` requests
  count toward `taken`, a refused request contributes 0 by construction —
  balance is untouched, guaranteed by the read-time formula rather than by
  remembering not to run a deduction.

## Idempotency / Double-Deduction Prevention (Invariant 6, test #9)

Because `taken` is computed as `SUM(... WHERE status = APPROVED)` rather than
mutated imperatively, "approving the same request twice" cannot double-deduct:
the request contributes exactly one row to the SUM regardless of how many
times the approve action is (attempted to be) invoked. The approve operation
itself must still be guarded at the service layer:

```
function approveRequest(requestId, actingUser):
    request = TimeOffRequest.find(requestId)
    if request.status != PENDING:
        return ERROR("Request is not pending; cannot approve")  # no-op, not a silent success
    if type.requires_allocation and request.duration > remainingBalance(request.employee, request.type):
        return ERROR("Insufficient balance")
    request.status = APPROVED
    request.decided_by = actingUser
    request.decided_at = now()
    save(request)
```

The `status != PENDING` guard is what makes the operation state-safe: a
duplicate approve call (double-click, retry) on an already-`APPROVED` request
is rejected rather than reprocessed, satisfying "avoid double deduction if the
same request is processed twice" (0.15) even though the SUM-based balance
already makes actual double-counting structurally impossible.

## Allocation Status

Allocations themselves also carry a `status` (`DRAFT/PENDING/APPROVED/REFUSED`)
per 0.14 — only `APPROVED` allocations feed the `allocated` sum. This mirrors
the request lifecycle for consistency and lets HR provisionally create an
allocation before it's confirmed.
