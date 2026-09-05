# Domain Terms

Canonical terminology across all PeoplePay360 systems:

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
