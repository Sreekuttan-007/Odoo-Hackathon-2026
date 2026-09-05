# Domain Terms

Canonical terminology across all Payloom systems:

- **User**: A system login account (has an email and password).
- **Employee**: The core HR personnel record. Not all employees may be Users.
- **Department**: A structural group of employees.
- **Contract**: Legal working conditions, salary, and validity dates for an Employee.
- **Working Schedule**: Defines expected working hours (e.g. 40 Hours/Week).
- **Attendance**: Time tracking records.
- **Time Off Type**: Categories of leave (Sick, Vacation).
- **Time Off Allocation**: Total leave granted to an employee.
- **Time Off Request**: A request by an employee to take time off.
- **Salary Structure**: The collection of rules dictating how a Payslip is calculated.
- **Salary Rule**: Individual formula (e.g., Basic, HRA, Tax).
- **Payrun**: A batch of Payslips generated for a Payroll Period.
- **Payslip**: Individual salary record for a specific employee.
- **Payroll Period**: The date range for a Payrun.
- **Payroll Dashboard**: High level metrics summary.

## Canonical Roles
- `EMPLOYEE`: Basic self-service access
- `HR_MANAGER`: Can manage employees and time off
- `HR_PAYROLL_USER`: Can process payruns
- `HR_PAYROLL_MANAGER`: Can configure payroll rules
- `ADMIN`: Full system access and user management

## Status Conventions
- `ACTIVE` → Active
- `INACTIVE` → Inactive

Note: `User.status` (account/login access) and `Employee.status` (employment
status) are separate concepts, even though both use the `ACTIVE`/`INACTIVE`
enum values. Deactivating a login does not change employment status and
vice versa.

## Employee ↔ Contract ↔ Working Schedule (Phase 2)

- **Employee** is the central HR record. It does *not* store salary or
  employment-term history directly — those live on **Contract** so an
  employee can have multiple contracts over time without overwriting
  history.
- **Contract** snapshots the Department, Job Position and Working Schedule
  that applied *during that contract*, rather than assuming the Employee's
  current master data is correct for historical periods. This matters for
  payroll correctness later.
- **Working Schedule** separately defines expected working time, independent
  of any one employee or contract. It can be referenced as an Employee's
  default schedule and/or overridden per Contract.
- **Precedence**: when both an Employee and its Contract carry a working
  schedule, the Contract's working schedule takes precedence; the Employee's
  is the fallback when the Contract has none set. This precedence is a
  documented policy, not yet enforced by a dedicated resolver function —
  Attendance/Payroll phases should implement `resolveWorkingSchedule(employee,
  contract)` accordingly when they consume it.

## Contract Reference
- Format: `CON/{year}/{sequence:04d}` (e.g. `CON/2026/0042`), generated
  server-side and sequential per calendar year of the contract's start date.
  The database primary key remains a plain integer id; the reference is the
  human-facing business identifier.

## Contract Status (derived, not persisted)
- `RUNNING` — `start_date <= today` and (`end_date` is null or `>= today`)
- `UPCOMING` — `start_date > today`
- `EXPIRED` — `end_date < today`

Deriving status from dates means it can never drift out of sync with the
dates (e.g. an `EXPIRED` contract flagged `RUNNING` by mistake is structurally
impossible).

## Contract Overlap Policy
Two Contracts belonging to the **same Employee** may never have overlapping
validity periods ( `[start_date, end_date]`, with `end_date = null` meaning
open-ended/infinite). This is enforced by the backend on both create and
update — never just a UI warning. See `app/services/contract_rules.py`.

## Period-Applicable Contract (for later Payroll)
`getApplicableContract(employee_id, period_start, period_end)` — implemented
in `app/services/contract_rules.py` and exposed at
`GET /api/contracts/applicable` — returns the one Contract whose validity
period overlaps the given payroll period:
- **Zero** matches → `MISSING_CONTRACT` (never silently skipped).
- **More than one** match → `CONTRACT_CONFLICT` (never silently resolved by
  picking "the latest" or similar).
- Exactly one match → returned.

Because overlapping contracts are already rejected at write time, a conflict
should only arise from data written before that rule existed (or a future
policy change permitting mid-period contract changes) — the service still
detects and reports it rather than assuming it can't happen.

## Working Schedule Calculation
For a schedule line: `worked_hours = (end_time - start_time - break_minutes) /
60`. A schedule's `hours_per_week` is the sum of every line's worked hours;
`days_per_week` is the count of distinct days with a line. Both are always
computed from the lines — never stored/editable independently — so they
cannot drift out of sync with the pattern. Overnight shifts (`end_time <=
start_time`) are deferred: rejected outright rather than silently
miscalculated.

## Deferred: Salary Structure
Contract carries an optional `salary_structure_note` free-text field as a
placeholder. No `SalaryStructure` model exists yet — building one now would
mean fabricating payroll configuration data ahead of that phase. The
relationship is deferred until the Salary Structure module is built.

## Working Schedule vs. Attendance (Phase 3)
**Working Schedule = expected time. Attendance = actual time.** Attendance
never mutates Working Schedule; it only reads an employee's schedule to
compute overtime for a given day.

## Attendance Model Decisions
- **One record per employee per company-timezone day** (`Asia/Kolkata`), not
  a multi-shift model. This was chosen for MVP simplicity — see
  `app/services/attendance_rules.py`.
- **Session state is derived, not stored**: `check_in` present + `check_out`
  null → `ACTIVE` (if today) or `MISSING_CHECKOUT` (if a past date — a stale
  unclosed session); both present → `COMPLETED`. There is no separate
  `status` column.
- **Check-in blocking**: rejected if the employee has *any* open session
  (any date) or already has a record for today. This makes the
  one-record-per-day rule and the stale-missing-checkout case both
  enforceable with a single rule.
- **Timezone policy**: all timestamps are stored in UTC
  (`DateTime(timezone=True)`); "today" and `attendance_date` are always
  computed by converting to `Asia/Kolkata` first, never compared as naive
  UTC-midnight dates. SQLite drops tzinfo on round-trip, so every timestamp
  read back from the database is re-normalized to UTC (`as_utc()`) before
  any comparison — otherwise naive/aware comparisons raise at runtime.
- **Overtime** is implemented (not deferred): for a completed record,
  `overtime = max(0, worked_minutes - expected_minutes)` where
  `expected_minutes` comes from the employee's Working Schedule line
  matching that day's weekday. Returns `null` — never `0` — when the
  employee has no schedule, the schedule has no line for that weekday, or
  the session is still open. Never converted to salary; that's a later
  Payroll concern.
- **Absence** is not persisted this phase. Attendance records represent
  actual attendance events only; absence should be derived later in
  reporting against Working Schedule, not backfilled as empty rows here.
- **Corrections**: HR-capable roles only. A correction can change
  `check_in`/`check_out`/`notes`; `worked_minutes`/`overtime_minutes` are
  always recomputed from the (possibly corrected) timestamps, never
  independently edited. `corrected_by_user_id` records who made the last
  correction (single mutable record, not a full correction history table —
  an MVP simplification). A correction that would overlap another
  Attendance record for the same employee is rejected
  (`409 ATTENDANCE_OVERLAP`).

## Time Off Model Decisions (Phase 4)
- **Three-tier model**: `TimeOffType` defines policy (unit, whether an
  allocation is required, approval policy). `TimeOffAllocation` defines
  entitlement for one employee/type/validity period. `TimeOffRequest`
  represents actual usage and only consumes entitlement once approved.
- **Balance is never persisted.** `taken` is always the live sum of
  `duration_amount` across APPROVED requests linked to an allocation;
  `remaining = allocated_amount - taken`. Pending and refused requests
  always contribute `0` — this is what makes double-approval structurally
  unable to double-deduct (approving an already-APPROVED request is
  rejected outright, `409 ALREADY_DECIDED`, before any balance math runs).
- **Duration is a snapshot.** `TimeOffRequest.duration_amount` is computed
  once at creation time from the employee's Working Schedule and stored —
  not recomputed on every read — so a later schedule change can't
  retroactively alter a historical request.
  - `DAYS` unit: count of scheduled working days in `[start_date,
    end_date]`, matching the employee's Working Schedule weekday lines. No
    schedule -> documented fallback to a calendar-day count (not silently
    guessed as "all working days").
  - `HOURS` unit: sum of each scheduled day's expected hours from the
    Working Schedule. No schedule -> rejected outright
    (`400 NO_WORKING_SCHEDULE`), since there's no safe fallback for hours.
  - A period with zero scheduled working days (e.g. a weekend-only range)
    is rejected (`400 NO_WORKING_DAYS`), never silently zero.
- **Allocation uniqueness**: only one APPROVED allocation per
  (employee, time_off_type, overlapping validity period) is allowed —
  enforced at approval time (`409 ALLOCATION_OVERLAP`), since creation
  can precede approval by any amount of time.
- **Allocation resolution for a request**: the one APPROVED allocation
  whose validity period fully covers the request's `[start_date,
  end_date]`. Zero matches -> `404 NO_ALLOCATION`; more than one (only
  reachable from data predating the uniqueness rule) -> `409
  AMBIGUOUS_ALLOCATION`, never silently picked.
- **Approval is a single transaction**: re-validate the request is still
  `TO_APPROVE`, re-resolve the allocation, re-check remaining balance
  against `duration_amount`, then mark `APPROVED`. Self-approval is always
  blocked (`403 SELF_APPROVAL`) regardless of role — including an HR
  Manager approving their own request — since Employee-Manager-User
  hierarchies aren't reliable enough yet to route to a different approver
  automatically (documented simplification of `approval_policy`: the field
  is stored and shown for transparency, but actual enforcement today is
  "any HR-capable role, except never the request's own employee").
- **Overlap protection**: an employee cannot hold two
  `TO_APPROVE`/`APPROVED` Time Off Requests with overlapping date ranges
  (`409 REQUEST_OVERLAP`); touching endpoints count as overlapping.
- **Auto-approval**: a Time Off Type with `approval_policy = NONE` marks
  new requests `APPROVED` immediately (still subject to the same balance
  check when it requires an allocation).
- **Deferred**: "My Team" filtering (manager hierarchy isn't reliable
  enough yet — not faked as a no-op toggle), a Time Off dashboard,
  multi-level approvals, accrual automation, carry-forward, public
  holidays, and any Attendance/Payroll integration from approved leave.

## Payroll Model Decisions (Phase 5)
- **Four entities, one direction of truth**: `SalaryStructure` groups
  ordered `SalaryRule`s (HOW pay is calculated). A `Payrun` fixes WHEN
  (period) and WHO (explicitly selected employees) for one payroll batch.
  Each selected employee gets exactly one `Payslip` (WHAT they're paid),
  and every `Payslip` carries `PayslipLine` rows (WHY — the rule-by-rule
  trace). Basic/Allowances/Gross/Deductions/Net on a Payslip are always the
  sum of that Payslip's line amounts grouped by category — GROSS and NET
  are themselves ordinary rules (typically FORMULA) that an admin defines;
  the engine never invents a total independently of the rules.
- **Rule execution is sequence-ordered and forward-reference-safe**: rules
  run by `sequence` ascending; a rule can read an earlier rule's result
  (`rules["CODE"]`) or running category total (`categories["CATEGORY"]`),
  and both dicts only ever contain what has already executed — so a
  forward reference fails with a specific, visible error rather than
  silently resolving to zero or being merely a style guideline.
- **FORMULA rules use a constrained AST evaluator**
  (`app/services/formula_engine.py`), not `eval()`/`exec()`. It whitelists
  numeric literals, +-*/%**, unary +/-, and `rules["CODE"]` /
  `categories["CATEGORY"]` subscripts — no attribute access, calls,
  imports, or comprehensions, so there is no path to builtins regardless
  of what an admin types into the formula field.
- **Money is Decimal end-to-end**, quantized to 2dp with ROUND_HALF_UP at
  the point each rule produces its amount.
- **A rule computation failure is a BLOCKER, never a silent 0.** The
  PayslipLine for that rule is omitted and a `RULE_FAILURE`
  `PayrollWarning` is attached; any later rule depending on it fails too
  (its code is simply absent from `rules`), so the failure is visible
  everywhere it propagates.
- **Payrun state machine**: `DRAFT -> COMPUTED -> VALIDATED -> PAID`,
  strictly forward, enforced server-side (`409 INVALID_TRANSITION` on any
  other attempted move). Recompute is allowed from DRAFT/COMPUTED (clears
  and rebuilds that Payslip's lines/warnings deterministically — never
  duplicates them) but never from VALIDATED/PAID. Validate re-runs compute
  once more immediately before checking for blockers (a fresh preflight),
  and refuses to proceed (`409 VALIDATION_BLOCKED`) if any Payslip still
  has a BLOCKER-severity warning.
- **Eligibility is re-validated server-side at creation**, never trusting
  the wizard's client-side preview: an employee needs an unambiguous
  applicable Contract (reusing `contract_rules.get_applicable_contract()`
  from Phase 2) with a positive wage, and no existing Payslip for an
  overlapping period in any other Payrun. If any selected employee fails
  this, the whole creation is rejected (`409 INELIGIBLE_EMPLOYEES`) rather
  than silently dropping them.
- **The wizard's "Continue" is a GET** (`/payroll/payruns/eligible-employees`)
  — it is structurally incapable of creating a Payrun, since only `POST
  /payroll/payruns` (Step 2's "Create Payrun") does that.
- **Historical snapshots are real**: each PayslipLine freezes the rule's
  name/code/category/sequence/method/amount at compute time. Editing a
  Salary Rule afterward changes only *future* computations — a
  VALIDATED/PAID Payslip's numbers and PDF never change, because nothing
  ever recomputes them again.
- **Context exposed to rules**: `contract_wage`, `worked_days` (Attendance
  records with a check_out in the period), `expected_work_days` (scheduled
  working days per the employee's Working Schedule), `worked_hours`,
  `overtime_hours`, and `approved_leave_days` (approved DAYS-unit Time Off
  Requests overlapping the period — HOURS-unit leave isn't counted here,
  and paid vs. unpaid leave isn't distinguished, since TimeOffType has no
  such flag yet). Attendance/Time Off data is exposed as context only;
  whether and how it affects pay is entirely up to how a Salary Rule's
  formula uses it — the engine never reduces pay on its own.
- **Deferred**: mid-period contract changes beyond the existing
  zero/one/many applicable-contract resolution (no proration), a
  paid/unpaid leave distinction, a Payroll Dashboard (next phase), real
  email delivery of payslips (no mail provider is configured in this
  environment — "Send Payslips" is intentionally not built rather than
  faked), and any statutory/compliance claim (rules named PF/PT are
  calculation examples only, not statutory filings).

## Phase 7 — PayTrace

- **PayTrace** is a read-only explanation layer over an already-computed
  Payslip — it never calculates payroll itself. `GET
  /api/payroll/payslips/{id}/trace` rebuilds a structured, deterministic
  trace entirely from each `PayslipLine`'s own snapshot fields, never from
  the current `SalaryRule` row or `Contract`. This is a stronger guarantee
  than "historical snapshots are real" above: it means PayTrace survives
  not just a Salary Rule edit but also a Contract wage edit after the
  Payslip was computed, because `PayslipLine.base_amount_snapshot`
  captures the resolved Contract Wage (or referenced rule's amount) used
  at that moment, not a live lookup.
- **Calculation Trace**: one entry per `PayslipLine`, in rule `sequence`
  order (never alphabetized), each carrying its computation method
  (FIXED/PERCENTAGE/FORMULA), a structured `calculation` object specific
  to that method, a human `explanation` string, and `depends_on` — the
  other rule codes (if any) this entry's amount was derived from, used
  for the UI's hover-to-highlight dependency feature.
  - FIXED: `fixed_amount_snapshot` (+ quantity if not 1).
  - PERCENTAGE: `percentage_snapshot`, `base_code_snapshot` ("CONTRACT_WAGE"
    or another rule's code), `base_amount_snapshot` (that base's resolved
    value at compute time).
  - FORMULA: the formula text (reused from the existing
    `base_description_snapshot`) plus `formula_inputs_snapshot` — a JSON
    map of every `rules["CODE"]`/`categories["CODE"]`/context-variable
    name the formula actually referenced, resolved to its value at that
    same compute time. Extracted via `formula_engine.extract_inputs()`, a
    read-only AST walk that mirrors (but never replaces) the existing
    whitelisted `evaluate_formula()` — it cannot execute anything the
    safe evaluator wouldn't already have executed.
- **Legacy Payslips**: lines computed before Phase 7 have `NULL` for all
  five new snapshot columns. PayTrace reports `has_structured_history:
  false` for those and falls back to the pre-existing
  `base_description_snapshot` string rather than fabricating structured
  numbers it doesn't actually have.
- **AI Narrator** (`GET .../trace/explain`, Phase 7B) is optional and
  strictly explanatory: it receives only the already-built deterministic
  trace (rule codes/categories/methods/amounts, the employee's first name,
  the period) — never DB access, never the ability to compute payroll.
  Gated by the optional `ANTHROPIC_API_KEY` env var; unset in this
  environment, so the endpoint has been exercised only through its
  fallback path (`available: false, reason: "NOT_CONFIGURED"`), plus unit
  tests simulating a timeout and a malformed/hallucinating response —
  not against a live provider call. Any failure (missing key, timeout,
  rate limit, malformed output) degrades to `available: false`; it never
  raises, and the deterministic `/trace` endpoint is unaffected regardless
  of this endpoint's outcome. The model's output is validated before use:
  any `components[].rule_code` not matching a real rule code in the trace
  sent to it is silently dropped.

## Phase 8 — Payroll Preflight

- **Payroll Preflight** is a deterministic *payroll readiness & risk
  engine* (`app/services/preflight.py`). It inspects an already-computed
  Payrun and surfaces real payroll problems BEFORE validation / payment.
  It is a **derived assessment** — it persists nothing and introduces no
  new Payrun status. The canonical state machine (DRAFT → COMPUTED →
  VALIDATED → PAID) is untouched; Preflight is a *gate* between COMPUTED
  and VALIDATED, expressed as a separate `readiness` value.
- **Readiness** (`NOT_RUN` / `ACTION_REQUIRED` / `REVIEW_RECOMMENDED` /
  `READY`) is purely a function of finding counts: any BLOCKER →
  `ACTION_REQUIRED`; else any WARNING → `REVIEW_RECOMMENDED`; else `READY`.
  `NOT_RUN` is only returned for a `DRAFT` Payrun.
- **Severity reuse**: Preflight uses the existing `WarningSeverity`
  vocabulary (`BLOCKER` / `WARNING` / `INFO`) — it is not a second warning
  system. It also *bridges* the compute engine's own BLOCKER/WARNING
  `PayrollWarning`s (e.g. `RULE_FAILURE`) into its findings, so one
  coherent readiness view covers both.
  - **BLOCKER**: payroll must not be validated until resolved — missing /
    conflicting applicable contract, duplicate Payslip, missing or
    ruleless Salary Structure, a rule-execution failure, persisted totals
    disagreeing with the calculation lines, negative Net.
  - **WARNING**: may proceed, explicit review recommended — large Net
    variance vs. the previous Payslip, deductions exceeding gross,
    incomplete Attendance in the period, an over-long Attendance session,
    worked days well above the schedule.
  - **INFO**: context, no risk — approved Time Off overlapping the period,
    no previous Payslip to compare, a contract starting/ending mid-period.
- **A finding** carries: `code` (stable id), `severity`, `category`,
  `message`, `employee_id` / `employee_name` / `payslip_id` where
  applicable, an `evidence` object (concrete numbers/refs — never "looks
  unusual"), and a `resolution` string where an action is known.
- **Checks are a registry** (`PREFLIGHT_CHECKS`), each a `PreflightCheck`
  (`code`, `name`, `category`, `evaluate(context)`), run against a single
  `PreflightContext` built once per run (one batched query per dimension,
  no per-employee query storms). A check that raises unexpectedly becomes
  a BLOCKER `PREFLIGHT_CHECK_ERROR` — Preflight fails *safe*, never
  silently READY.
- **Thresholds are centralised** in `preflight.THRESHOLDS`
  (`PreflightThresholds`): Net variance is flagged only when it crosses
  **both** a percentage bar (default 25%) **and** a minimum absolute
  rupee bar (default ₹5,000), so a tiny salary swinging a large % — or a
  large salary nudged a few rupees — produces no noise. Attendance
  anomaly bars (max single session 16h; worked-days ratio 1.5×) live in
  the same object.
- **Salary variance** compares the current Payslip's Net against the most
  recent *strictly-earlier, already-computed* Payslip for the same
  employee in any other Payrun. It reports `previous_net`, `current_net`,
  `absolute_delta`, `percentage_delta` — and never calls the change
  "wrong", only "review recommended". No previous Payslip → an INFO
  `NO_PREVIOUS_PAYSLIP`, never a variance WARNING.
- **Attendance**: Preflight only *reads* Attendance as context (this
  engine never derives pay from Attendance unless a Salary Rule formula
  explicitly uses `worked_*`). It flags incomplete records (no check-out)
  inside the period and implausibly long single sessions; it does not
  invent an Attendance→pay dependency.
- **Time Off**: approved Time Off overlapping the period is surfaced as
  **INFO only**, with an explicit note that pay is not reduced for leave
  unless a formula uses `approved_leave_days`. Preflight never claims a
  deduction that did not happen.
- **PayTrace integration**: Preflight *identifies* risk (e.g. "Net
  increased 80%"); PayTrace *explains* the calculation. Variance / integrity
  findings deep-link to the Payslip's PayTrace rather than duplicating it.
- **The validation gate is server-side and independent of the client**
  (spec sections 10/36/65): `payroll_engine.validate_payrun` recomputes
  every Payslip, then calls `preflight.evaluate_findings()` and aborts the
  transaction (`409 VALIDATION_BLOCKED`) if any blocker exists. A stale
  "READY" from the UI, or a direct API call, cannot bypass it — the check
  runs against current data every time.
- **No bank / payment details check**: the `Employee` model has no
  bank/payment fields, and Payloom marks payroll paid without executing
  any transfer. The "missing payment details" check from the spec is
  therefore intentionally **not implemented** — there is no field to
  inspect and nothing would be actionable. Future scope if such fields
  are added.
- **No AI, no risk score**: the engine is 100% deterministic. There is no
  "payroll safety score" — BLOCKER / WARNING / INFO with evidence is the
  whole model. An optional AI layer could later *summarise* already-
  classified findings, but is out of scope for this phase and would never
  classify severity or decide whether validation is allowed.
