# DOMAIN MODEL — PeoplePay360

## Core Domain Flow

```
EMPLOYEE
   |
   +--> CONTRACT (historical, period-scoped)
   +--> WORKING SCHEDULE (weekly pattern)
   |
   v
ATTENDANCE  +  TIME OFF (allocation -> request -> approval -> balance)
   |
   v
SALARY STRUCTURE (ordered container of Salary Rules)
   |
   v
SALARY RULE ENGINE
   (sequence: BASIC -> ALLOWANCE -> GROSS -> DEDUCTION -> NET,
    each rule reads a running calculation context)
   |
   v
PAYRUN  (two-step creation: Step1 scope -> Step2 employee selection -> CREATE)
   |
   v
PAYSLIP (+ PayslipLine per executed rule, frozen at computation time)
   |
   v
VALIDATION  (warnings vs blocking errors)
   |
   v
PAID  (status transition, history preserved)
   |
   v
PDF / EMAIL  (delivery, decoupled from calculation)
   |
   v
PAYROLL DASHBOARD  (pure aggregation of the above; no independent data)
```

The Employee is the hub: every other entity in the flow either belongs to an
Employee directly, or belongs to something that belongs to an Employee
(e.g. PayslipLine belongs to Payslip belongs to Employee).

## Entities (Business-Level Description)

### User
Login identity + role. Not the same as Employee (an Admin/HR user may not be
an employee in the payroll sense, though usually is).
- Relationships: `User 1—0..1 Employee` (optional link), `User many—1 Role` (or enum).

### Role
One of `EMPLOYEE`, `HR_MANAGER`, `HR_PAYROLL_USER`, `HR_PAYROLL_MANAGER`, `ADMIN`.
Modeled as an enum on `User` for MVP simplicity (no need for a many-to-many
permission table given only 5 fixed roles).

### Employee
The central business entity. Everything else hangs off it.
- Belongs to a Department, a Manager (self-referencing Employee), a Job Position,
  a Working Schedule (current default).
- Has many Contracts, Attendance records, Time Off Requests, Allocations, Payslips.

### Department
Simple lookup entity (name, optionally a head/manager). Used for grouping and
dashboard aggregation (headcount, salary cost by department).

### JobPosition
Simple lookup entity (title). Kept separate from Department so an employee's
title and their org unit vary independently.

### Contract
The **legal, period-scoped source of truth for pay terms**. An employee has a
history of contracts; only one should be `ACTIVE` and applicable at any given
date range for payroll purposes (see CONTRACT_RULES.md). Never overwritten —
superseded contracts remain in history with status `EXPIRED`/`TERMINATED`.

### WorkingSchedule / WorkingScheduleLine
Defines expected weekly working time as a pattern of lines (one or more per
day: start, end, break). Weekly hours are **always derived** from the lines,
never stored as an independent editable total.

### Attendance
One record per employee per work session (MVP: one per employee per date).
Captures actual check-in/check-out and derives worked hours plus an exception
status. Supports a simple correction trail when HR edits a record.

### TimeOffType
Leave policy definition (name, unit DAYS/HOURS, whether it requires an
allocation, whether it requires approval).

### TimeOffAllocation
An entitlement grant to an employee for a given Time Off Type and validity
window. Only `APPROVED` allocations count toward balance.

### TimeOffRequest
An employee's ask to consume leave. Lifecycle: `PENDING -> APPROVED/REFUSED`.
Approval is the only event that consumes an allocation.

### SalaryStructure
A named, ordered container of Salary Rules (e.g. "Regular Salary"). Selected
per Payrun/Contract; does not itself hold calculation logic.

### SalaryRule
A single computable line item (BASIC, an allowance, a deduction, etc.) with a
`computation_type` (FIXED / PERCENTAGE / FORMULA), a `category`, and a
`sequence` that determines execution order within a structure.

### SalaryStructureRule (join entity)
Many-to-many between SalaryStructure and SalaryRule, carrying the
structure-specific sequence (the same SalaryRule could in principle be reused
across structures with different ordering — MVP may keep 1 structure : many
rules with sequence stored directly on the join row).

### Payrun
A batch payroll operation: one Salary Structure + one payroll period + a
chosen set of employees. Owns many Payslips. State machine: `DRAFT ->
COMPUTED -> VALIDATED -> PAID` (see PAYRUN_STATE_MACHINE.md).

### Payslip
One employee's computed pay for one Payrun/period, built from their applicable
Contract + the Payrun's Salary Structure. Owns many PayslipLines.

### PayslipLine
The frozen, per-rule computed result (rule code, category, sequence, amount).
This is what makes a Payslip auditable and historically stable even if the
SalaryRule configuration changes later.

### PayrollWarning
A non-blocking (or blocking, depending on severity) issue surfaced during
validation, attached to a Payrun or Payslip (e.g. missing bank details,
duplicate payslip, missing contract).

## Historical-Data Considerations

- **Contracts**: never deleted/overwritten on change; a new contract row is
  inserted and the prior one's status transitions to `EXPIRED`/`TERMINATED`.
- **Payslips/PayslipLines**: immutable once `VALIDATED`; correction requires a
  new compensating record or an explicit "reversal" workflow, never an
  in-place edit of paid data.
- **Salary Rule changes**: affect only *future* payroll runs. Past Payslips
  read from their own frozen PayslipLines, not from the live SalaryRule table.
- **Deactivation over deletion**: Employees, SalaryRules, WorkingSchedules, etc.
  use an `active` boolean rather than hard delete, so historical references
  (a past Payslip's rule, a past Contract's schedule) never dangle.
