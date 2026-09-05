# API Contract

## General Conventions
- All APIs live under `/api/`
- Standard JSON responses
- Error shape:
```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable message",
    "details": null
  }
}
```
- Write endpoints (POST/PATCH) on Employees, Contracts, Departments, Job
  Positions and Working Schedules require an HR-capable role (`HR_MANAGER`,
  `HR_PAYROLL_USER`, `HR_PAYROLL_MANAGER`, `ADMIN`). Any authenticated user
  may read (`GET`).

## Foundation Endpoints
- `GET /api/health` - Healthcheck

## Authentication
- `POST /api/auth/login`
- `GET /api/auth/me`

## Admin Users (Phase 1)
- `GET/POST /api/admin/users`
- `PUT /api/admin/users/{id}`
- `GET /api/admin/employees/lookup` — employees without a User account yet
  (returns the minimal `{id, first_name, last_name, work_email}` shape)

## Departments
- `GET /api/departments?search=`
- `POST /api/departments` `{name}`
- `PATCH /api/departments/{id}` `{name}`

## Job Positions
- `GET /api/job-positions?search=`
- `POST /api/job-positions` `{title}`
- `PATCH /api/job-positions/{id}` `{title}`

## Employees
- `GET /api/employees?search=&department_id=&job_position_id=&status=&skip=&limit=`
  - `search` matches first name, last name, work email, employee code, or job
    position title.
- `GET /api/employees/{id}`
- `POST /api/employees`
- `PATCH /api/employees/{id}`
- Body fields: `first_name, last_name, work_email, work_location, status,
  department_id, job_position_id, manager_id, working_schedule_id`.
- `employee_code` is server-generated (`EMP0001`, …), not client-supplied.
- Validation: `department_id`/`job_position_id`/`working_schedule_id`/
  `manager_id` must reference existing rows; an employee cannot be its own
  manager (`INVALID_MANAGER`).
- Response includes `contracts_count` (real, computed from stored Contracts)
  and nested `department`, `job_position`, `manager`, `working_schedule`
  summaries.

## Contracts
- `GET /api/contracts?employee_id=&status=&search=`
  - `status` filters on the *derived* status (`RUNNING`/`UPCOMING`/`EXPIRED`).
  - `search` matches the contract reference.
- `GET /api/contracts/{id}`
- `GET /api/contracts/applicable?employee_id=&period_start=&period_end=`
  — exposes `getApplicableContract()` (see docs/DOMAIN_TERMS.md). Returns the
  single covering contract, `404 MISSING_CONTRACT`, or `409 CONTRACT_CONFLICT`.
- `POST /api/contracts`
- `PATCH /api/contracts/{id}`
- Body fields: `employee_id` (create only), `department_id, job_position_id,
  working_schedule_id, start_date, end_date, wage_monthly, currency,
  salary_structure_note`.
- `reference` is server-generated (`CON/{year}/{seq:04d}`).
- `status` in the response is always derived from dates, never persisted.
- Overlap validation runs on create and update: two contracts for the same
  employee may never have overlapping validity periods. Violation returns
  `409 CONTRACT_OVERLAP` with the conflicting contract's id/reference.

## Working Schedules
- `GET /api/working-schedules?search=&status=`
- `GET /api/working-schedules/{id}`
- `POST /api/working-schedules`
- `PATCH /api/working-schedules/{id}`
- Body: `name, company, timezone, status, lines[]` where each line is
  `{day_of_week, start_time, end_time, break_minutes}`.
- Sending `lines` on `PATCH` **replaces** the full weekly pattern.
- `days_per_week` and `hours_per_week` are always computed from `lines`,
  never accepted as input.
- Per-line `derived_hours` is computed the same way:
  `(end_time - start_time - break_minutes) / 60`.
- Employee responses also include `attendance_count` (real, computed from
  stored Attendance records).

## Attendance
- `POST /api/attendance/check-in` — self-service; resolves the employee from
  the authenticated user's `employee_id` (never a client-supplied id).
  `409 ALREADY_CHECKED_IN` if an open session exists (any date — catches a
  stale missing-checkout); `409 ALREADY_RECORDED_TODAY` if today's record
  already exists (one record per employee per company-timezone day).
- `POST /api/attendance/check-out` — self-service. `409 NO_OPEN_SESSION` if
  there's nothing to check out of.
- `GET /api/attendance/current` — `{checked_in, attendance}` for the quick
  widget. `attendance` is `null` when not checked in. The frontend timer is
  display-only; this endpoint (backed by the persisted `check_in`) is the
  source of truth on reload.
- `GET /api/attendance?employee_id=&on_date=&date_from=&date_to=&status=`
  — `EMPLOYEE`-role callers are always scoped to their own records
  regardless of `employee_id`; HR-capable roles may pass `employee_id` to
  filter, or omit it to see everyone. `status` filters on the *derived*
  status (`ACTIVE`/`MISSING_CHECKOUT`/`COMPLETED`).
- `GET /api/attendance/{id}` — `403` if the caller is neither HR-capable nor
  the record's own employee.
- `PATCH /api/attendance/{id}` — HR-capable only (correction). Body:
  `check_in?, check_out?, notes?`. Sets `corrected_by_user_id` to the acting
  user. Rejects `check_out < check_in` (`422`, schema-level) and any edit
  that would overlap another Attendance record for the same employee
  (`409 ATTENDANCE_OVERLAP`).
- `worked_minutes`, `overtime_minutes`, and `status` are always derived from
  `check_in`/`check_out`/the employee's Working Schedule on every read —
  never persisted, never independently editable.
- `overtime_minutes` is `null` (not `0`) when the employee has no Working
  Schedule, or the schedule has no line for that weekday, or the session is
  still open — it is never faked.
- All timestamps are UTC. "Today" and each record's `attendance_date` are
  computed in the company timezone (`Asia/Kolkata`), not UTC midnight.

## Time Off Types
- `GET /api/time-off/types?search=&is_active=&unit=`
- `GET /api/time-off/types/{id}`
- `POST /api/time-off/types` (HR-capable) — `{name, code?, unit, requires_allocation, approval_policy, is_active, display_color?, notes?}`
- `PATCH /api/time-off/types/{id}` (HR-capable) — changing `unit` is rejected
  (`409 UNIT_LOCKED`) once any Allocation or Request references the type.

## Time Off Allocations
- `GET /api/time-off/allocations?employee_id=&time_off_type_id=&status=` —
  `EMPLOYEE`-role callers are always scoped to their own allocations.
- `GET /api/time-off/allocations/{id}` — `403` if not HR-capable and not the
  allocation's own employee.
- `POST /api/time-off/allocations` (HR-capable) — `{employee_id,
  time_off_type_id, allocated_amount, valid_from, valid_to, description?}`.
  Always created `TO_APPROVE`; `taken_amount`/`remaining_amount` are never
  client-supplied.
- `PATCH /api/time-off/allocations/{id}` (HR-capable) — only while
  `TO_APPROVE` (`409 ALREADY_DECIDED` otherwise).
- `POST /api/time-off/allocations/{id}/approve` (HR-capable) — rejects if
  not `TO_APPROVE` (`409 ALREADY_DECIDED`) or if another APPROVED
  allocation for the same employee/type already covers an overlapping
  period (`409 ALLOCATION_OVERLAP`).
- `POST /api/time-off/allocations/{id}/refuse` (HR-capable).
- `taken_amount`/`remaining_amount` are always derived: the sum of
  `duration_amount` across APPROVED requests linked to the allocation, and
  the difference from `allocated_amount`. Non-APPROVED allocations always
  report `0`/`0`.

## Time Off Requests
- `GET /api/time-off/requests?employee_id=&time_off_type_id=&status=` —
  `EMPLOYEE`-role callers are always scoped to their own requests.
- `GET /api/time-off/requests/{id}` — `403` if not HR-capable and not the
  request's own employee.
- `POST /api/time-off/requests` — self-service; `EMPLOYEE`-role callers may
  not set `employee_id` to another employee (`403 ACCESS_DENIED`).
  `{employee_id?, time_off_type_id, start_date, end_date, reason?}`.
  `duration_amount` is computed server-side (see docs/DOMAIN_TERMS.md) and
  stored as a snapshot. Errors: `400 TYPE_INACTIVE`, `400
  NO_WORKING_SCHEDULE`, `400 NO_WORKING_DAYS`, `404 NO_ALLOCATION`, `409
  AMBIGUOUS_ALLOCATION`, `409 INSUFFICIENT_BALANCE`, `409 REQUEST_OVERLAP`.
- `PATCH /api/time-off/requests/{id}` — owner or HR-capable, only while
  `TO_APPROVE` (`409 ALREADY_DECIDED` otherwise). Re-runs full duration/
  allocation/overlap validation when dates change.
- `POST /api/time-off/requests/{id}/approve` (HR-capable) — `403
  SELF_APPROVAL` if the caller is the request's own employee (even ADMIN);
  `409 ALREADY_DECIDED` if not `TO_APPROVE`; `404 NO_ALLOCATION` / `409
  INSUFFICIENT_BALANCE` re-checked at approval time for allocation-backed
  types.
- `POST /api/time-off/requests/{id}/refuse` (HR-capable) — same
  self-approval/already-decided guards; consumes no balance.
- `balance` in the response is `null` unless the request is linked to an
  allocation; otherwise it reports `{allocation_id, before, consumed,
  remaining}` reflecting the allocation's state after this request's
  current status is applied.

## Time Off Balance
- `GET /api/time-off/balance?employee_id=&time_off_type_id=&on_date=` —
  `EMPLOYEE`-role callers may only query their own balance
  (`403 ACCESS_DENIED` otherwise). Returns the APPROVED allocation covering
  `on_date` (default today), or all-zero if none exists.
- Employee responses also include `time_off_requests_count` (real, computed
  from stored Time Off Requests).

## Salary Structures & Rules
- `GET /api/payroll/structures?search=&is_active=` / `GET .../{id}` (detail
  includes ordered `rules[]`) — any authenticated user may read.
- `POST /api/payroll/structures` / `PATCH .../{id}` — `HR_PAYROLL_MANAGER`/
  `ADMIN` only (`HR_PAYROLL_USER` is read-only for configuration).
- `GET /api/payroll/rules?salary_structure_id=` / `GET .../{id}` — read-only
  for any authenticated user.
- `POST /api/payroll/rules?salary_structure_id=` / `PATCH .../{id}` —
  `HR_PAYROLL_MANAGER`/`ADMIN` only. `code` must be unique within its
  structure (`409 DUPLICATE_CODE`). `computation_method` is `FIXED`
  (`fixed_amount x quantity`), `PERCENTAGE` (`percentage% of
  percentage_base`, where `percentage_base` is `CONTRACT_WAGE` or an
  earlier rule's `code`), or `FORMULA` (a constrained expression — see
  docs/DOMAIN_TERMS.md).

## Payruns
- `GET /api/payroll/payruns/eligible-employees?salary_structure_id=&period_start=&period_end=`
  — read-only preview for the creation wizard's Step 1→2 "Continue"; never
  creates a Payrun. `HR_PAYROLL_USER`/`HR_PAYROLL_MANAGER`/`ADMIN` only.
- `GET /api/payroll/payruns` / `GET .../{id}` — same roles.
- `POST /api/payroll/payruns` — `{salary_structure_id, period_start,
  period_end, employee_ids}`. Re-validates every `employee_id`'s
  eligibility server-side; any ineligible selection rejects the whole
  request (`409 INELIGIBLE_EMPLOYEES`, with per-employee reasons). Creates
  the Payrun in `DRAFT` with exactly the selected employees' Payslips —
  never all employees matching the structure.
- `POST /api/payroll/payruns/{id}/compute` — `DRAFT`or `COMPUTED` only
  (recompute is idempotent, never duplicates lines); `409
  INVALID_TRANSITION` otherwise.
- `POST /api/payroll/payruns/{id}/validate` — `COMPUTED` only; recomputes
  once more, then requires zero BLOCKER-severity warnings across all
  Payslips or rejects with `409 VALIDATION_BLOCKED` (`details.blockers`
  lists the offending employees/messages).
- `POST /api/payroll/payruns/{id}/mark-paid` — `VALIDATED` only.
- `GET`/`POST /api/payroll/payruns/{id}/preflight` (Phase 8, Payroll Preflight) —
  `HR_PAYROLL_USER`/`HR_PAYROLL_MANAGER`/`ADMIN` only. Runs the deterministic
  Preflight engine against the current DB state and returns a derived
  readiness assessment. Read-only — persists nothing, never recomputes
  payroll, never mutates the Payrun; GET and POST are equivalent (POST
  exists so the UI's "Run again" reads as an action). A `DRAFT` Payrun
  returns `readiness: "NOT_RUN"` with empty findings. Otherwise:
  ```json
  {
    "payrun_id": 12, "reference": "PR/2026/0003", "status": "COMPUTED",
    "period": {"start": "2026-09-01", "end": "2026-09-30"},
    "employee_count": 8, "generated_at": "2026-09-06T...Z",
    "readiness": "ACTION_REQUIRED",
    "summary": {"blockers": 2, "warnings": 3, "info": 1},
    "findings": [
      {
        "code": "MISSING_APPLICABLE_CONTRACT", "severity": "BLOCKER",
        "category": "CONTRACT", "message": "...",
        "employee_id": 104, "employee_name": "Aarav Sharma", "payslip_id": 55,
        "evidence": {"period_start": "2026-09-01", "period_end": "2026-09-30"},
        "resolution": "Create or correct this employee's contract ..."
      }
    ],
    "message": null
  }
  ```
  `readiness` is purely a function of the counts: any BLOCKER →
  `ACTION_REQUIRED`; else any WARNING → `REVIEW_RECOMMENDED`; else `READY`.
  Finding `code`s are stable identifiers (`MISSING_APPLICABLE_CONTRACT`,
  `CONTRACT_CONFLICT`, `DUPLICATE_PAYSLIP`, `MISSING_SALARY_STRUCTURE`,
  `SALARY_STRUCTURE_HAS_NO_RULES`, `SALARY_STRUCTURE_HAS_NO_NET_RULE`,
  `PAYSLIP_TOTAL_MISMATCH`, `NEGATIVE_NET_PAY`, `DEDUCTIONS_EXCEED_GROSS`,
  `INCOMPLETE_ATTENDANCE`, `LONG_ATTENDANCE_SESSION`,
  `ATTENDANCE_ABOVE_SCHEDULE`, `APPROVED_TIME_OFF_IN_PERIOD`,
  `LARGE_NET_VARIANCE`, `NO_PREVIOUS_PAYSLIP`, `CONTRACT_STARTS_MID_PERIOD`,
  `CONTRACT_ENDS_MID_PERIOD`, plus any bridged compute-engine warning code
  such as `RULE_FAILURE`, and the fail-safe `PREFLIGHT_CHECK_ERROR`).
- `POST /api/payroll/payruns/{id}/validate` now additionally re-runs the
  full Preflight engine server-side after its recompute. On any blocker it
  rejects with `409 VALIDATION_BLOCKED`; `details.blockers` keeps the
  existing per-Payslip `{payslip_id, employee, messages}` shape and
  `details.findings` carries the complete Preflight finding list. This is
  the stale-Preflight guard — a blocker introduced after the last UI
  Preflight still stops validation.
- There is no "Send Payslips" endpoint — no email provider is configured
  in this environment, and a fake success response is out of scope (see
  docs/DOMAIN_TERMS.md).

## Payslips
- `GET /api/payroll/payslips?payrun_id=&employee_id=&status=` —
  `EMPLOYEE`-role callers are always scoped to their own Payslips, and
  only `VALIDATED`/`PAID` ones (not yet "available"); HR-capable roles may
  filter by `employee_id`/`payrun_id` or omit them to see everyone,
  regardless of status.
- `GET /api/payroll/payslips/{id}` — `403` if the caller is neither
  HR-capable nor the Payslip's own employee, or if it's their own but not
  yet `VALIDATED`/`PAID`.
- `GET /api/payroll/payslips/{id}/pdf` — same access rule; returns a real
  generated PDF (`application/pdf`) built from the persisted, already
  -computed Payslip — never recomputed, so a VALIDATED/PAID Payslip's PDF
  stays historically stable even if its Salary Rules change afterward.
- `GET /api/payroll/payslips/{id}/trace` (Phase 7, PayTrace) — same access
  rule. Read-only; never recomputes. Returns `{"available": false, "reason":
  "NOT_COMPUTED"|"NO_LINES", "message": ...}` for an uncomputed Payslip or
  one with no lines (e.g. blocked before rule execution), never a
  fabricated trace. Otherwise returns a structured, deterministic
  explanation rebuilt entirely from each `PayslipLine`'s own snapshot
  fields (`fixed_amount_snapshot`/`percentage_snapshot`/`base_code_snapshot`/
  `base_amount_snapshot`/`formula_inputs_snapshot`) — never from the
  current (possibly since-edited) `SalaryRule` row, so a historical trace
  cannot shift when a live rule is edited afterward. Lines computed before
  Phase 7 lack these columns (`has_structured_history: false` in the
  response) and fall back to the pre-existing `base_description_snapshot`
  string rather than fabricating structured numbers.
- `GET /api/payroll/payslips/{id}/trace/explain?mode=employee|payroll`
  (Phase 7B, PayTrace AI Narrator — optional) — same access rule. Builds
  the deterministic trace above and asks an LLM (Anthropic, called via
  plain HTTP, gated by the optional `ANTHROPIC_API_KEY` env var) to
  restate it in plain language. Returns `{"available": false, "reason":
  "NOT_CONFIGURED"|"TIMEOUT"|"RATE_LIMITED"|"PROVIDER_ERROR"|
  "MALFORMED_RESPONSE"}` on any failure — including no key configured —
  rather than raising; the deterministic trace endpoint above is entirely
  unaffected by this endpoint's outcome. Any `components[].rule_code` the
  model returns is filtered against the trace's real rule codes before
  being returned, so a hallucinated reference can't pass through.
- `basic`/`allowances`/`gross`/`deductions`/`net` are always the sum of
  that Payslip's `lines[]` amounts grouped by category — never independently
  edited. `warnings[]` carries severity (`BLOCKER`/`WARNING`/`INFO`), code,
  and message for every issue found on that Payslip.
