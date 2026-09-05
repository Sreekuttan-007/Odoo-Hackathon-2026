# DATABASE SCHEMA (Conceptual ER Design) — PeoplePay360

No migrations are created in Phase 0. This is the schema design that Phase 1+
will translate into actual migrations (e.g. Prisma schema).

Convention: all primary keys are UUIDs (`id`). All tables get `created_at`,
`updated_at`. Soft-deactivation via `active` boolean is preferred over hard
delete for master/config data; transactional data (Contract, Payslip, Payrun)
uses status enums instead of an `active` flag.

## User
| Field | Type | Notes |
|---|---|---|
| id | uuid | PK |
| email | string, unique | login |
| password_hash | string | |
| role | enum(EMPLOYEE, HR_MANAGER, HR_PAYROLL_USER, HR_PAYROLL_MANAGER, ADMIN) | |
| employee_id | uuid FK -> Employee, nullable, unique | optional link |
| active | boolean | disable login without deleting |

## Department
| Field | Type | Notes |
|---|---|---|
| id | uuid | PK |
| name | string, unique | |
| active | boolean | |

## JobPosition
| Field | Type | Notes |
|---|---|---|
| id | uuid | PK |
| title | string | |
| active | boolean | |

## Employee
| Field | Type | Notes |
|---|---|---|
| id | uuid | PK |
| employee_number | string, unique | human-readable code |
| first_name / last_name | string | |
| email | string, unique | |
| phone | string, nullable | |
| department_id | uuid FK -> Department | |
| manager_id | uuid FK -> Employee, nullable | self-reference |
| job_position_id | uuid FK -> JobPosition | |
| employee_type | enum(FULL_TIME, PART_TIME, CONTRACTOR) | assumption, simplest set |
| working_schedule_id | uuid FK -> WorkingSchedule | current default schedule |
| bank_account_number, bank_name, bank_ifsc (or equivalent) | string, nullable | required before Mark Paid for that employee |
| active_status | enum(ACTIVE, INACTIVE) | |
| join_date | date | |

Indexes: `department_id`, `manager_id`, `email` (unique).

## Contract
| Field | Type | Notes |
|---|---|---|
| id | uuid | PK |
| employee_id | uuid FK -> Employee | |
| start_date | date | |
| end_date | date, nullable | null = open-ended |
| wage | decimal | monthly base wage |
| department_id | uuid FK -> Department | snapshot of dept at contract time |
| job_position_id | uuid FK -> JobPosition | snapshot of position at contract time |
| salary_structure_id | uuid FK -> SalaryStructure | |
| status | enum(DRAFT, ACTIVE, EXPIRED, TERMINATED) | see CONTRACT_RULES.md |

Constraint (application-enforced, documented for a DB check/trigger later):
no two contracts for the same employee with status `ACTIVE` may have
overlapping `[start_date, end_date]` ranges. See CONTRACT_RULES.md for the
conflict-detection algorithm (DB-level exclusion constraints are a valid
Phase-2 hardening, not required for MVP correctness if the service layer
enforces it transactionally).

Index: `(employee_id, start_date, end_date)`.

## WorkingSchedule
| Field | Type | Notes |
|---|---|---|
| id | uuid | PK |
| name | string | |
| type | enum(FULL_TIME, PART_TIME) | |
| active | boolean | |

`weekly_hours` is **not stored** — always derived from lines (see WORKING SCHEDULE algorithm).

## WorkingScheduleLine
| Field | Type | Notes |
|---|---|---|
| id | uuid | PK |
| working_schedule_id | uuid FK | |
| day_of_week | enum(MON..SUN) | |
| start_time | time | |
| end_time | time | must be > start_time |
| break_duration_minutes | int, >= 0 | |

## Attendance
| Field | Type | Notes |
|---|---|---|
| id | uuid | PK |
| employee_id | uuid FK -> Employee | |
| date | date | |
| check_in | timestamp, nullable | |
| check_out | timestamp, nullable | |
| worked_hours | decimal, derived | computed at check-out (or on correction) |
| status | enum(PRESENT, LATE, ABSENT, OVERTIME, MISSING_CHECK_OUT) | derived from schedule comparison |
| manually_edited | boolean, default false | |
| corrected_by | uuid FK -> User, nullable | |
| corrected_at | timestamp, nullable | |
| correction_reason | string, nullable | |

Unique constraint: `(employee_id, date)` — one attendance record per employee per day (MVP).

## TimeOffType
| Field | Type | Notes |
|---|---|---|
| id | uuid | PK |
| name | string | |
| unit | enum(DAYS, HOURS) | |
| requires_allocation | boolean | |
| requires_approval | boolean | |
| payroll_integration | enum(NONE, UNPAID_DEDUCTION, PAID) | assumption; drives whether a future salary rule reads this type |
| active | boolean | |

## TimeOffAllocation
| Field | Type | Notes |
|---|---|---|
| id | uuid | PK |
| employee_id | uuid FK -> Employee | |
| time_off_type_id | uuid FK -> TimeOffType | |
| allocated_amount | decimal | in the type's unit |
| validity_start | date | |
| validity_end | date, nullable | |
| status | enum(DRAFT, PENDING, APPROVED, REFUSED) | only APPROVED counts |

`taken` and `remaining` are **derived**, not stored (see LEAVE_RULES.md).

## TimeOffRequest
| Field | Type | Notes |
|---|---|---|
| id | uuid | PK |
| employee_id | uuid FK -> Employee | |
| time_off_type_id | uuid FK -> TimeOffType | |
| start_date | date | |
| end_date | date | |
| duration | decimal, derived | in type's unit |
| status | enum(PENDING, APPROVED, REFUSED, CANCELLED) | |
| decided_by | uuid FK -> User, nullable | |
| decided_at | timestamp, nullable | |

## SalaryStructure
| Field | Type | Notes |
|---|---|---|
| id | uuid | PK |
| name | string | |
| active | boolean | |

## SalaryRule
| Field | Type | Notes |
|---|---|---|
| id | uuid | PK |
| name | string | |
| code | string, unique | e.g. `BASIC`, `HRA`, `NET` — referenced by formulas |
| category | enum(BASIC, ALLOWANCE, GROSS, DEDUCTION, NET) | |
| computation_type | enum(FIXED, PERCENTAGE, FORMULA) | |
| value_config | jsonb | shape depends on computation_type (see SALARY_RULE_ENGINE.md) |
| active | boolean | |

## SalaryStructureRule (join)
| Field | Type | Notes |
|---|---|---|
| id | uuid | PK |
| salary_structure_id | uuid FK | |
| salary_rule_id | uuid FK | |
| sequence | int | execution order within this structure |

Unique constraint: `(salary_structure_id, salary_rule_id)`.

## Payrun
| Field | Type | Notes |
|---|---|---|
| id | uuid | PK |
| reference | string, unique | e.g. "PAYRUN-2026-08" |
| salary_structure_id | uuid FK -> SalaryStructure | fixed at Step 1 |
| period_start | date | |
| period_end | date | |
| status | enum(DRAFT, COMPUTED, VALIDATED, PAID, CANCELLED) | see PAYRUN_STATE_MACHINE.md |
| created_by | uuid FK -> User | |

## Payslip
| Field | Type | Notes |
|---|---|---|
| id | uuid | PK |
| payrun_id | uuid FK -> Payrun | |
| employee_id | uuid FK -> Employee | |
| contract_id | uuid FK -> Contract | the applicable contract resolved at compute time |
| salary_structure_id | uuid FK -> SalaryStructure | copied from Payrun for stability |
| period_start / period_end | date | copied from Payrun |
| worked_days | decimal | computed from attendance/schedule |
| status | enum(DRAFT, COMPUTED, VALIDATED, PAID, CANCELLED) | mirrors/tracks with Payrun but can be individually flagged |

**Unique constraint: `(employee_id, payrun_id)`** — the primary duplicate-payslip
guard (see 0.26). A secondary defensive constraint on
`(employee_id, period_start, period_end, salary_structure_id)` may be added if
multiple Payruns could ever target the same period (not expected in MVP, since
Payrun already scopes one structure + one period).

## PayslipLine
| Field | Type | Notes |
|---|---|---|
| id | uuid | PK |
| payslip_id | uuid FK -> Payslip | |
| salary_rule_id | uuid FK -> SalaryRule, nullable | kept for reference; nullable so line survives rule deletion |
| rule_code | string | **snapshotted**, not joined live |
| category | enum | **snapshotted** |
| sequence | int | **snapshotted** |
| amount | decimal | computed result |

Snapshotting `rule_code`/`category`/`sequence` (rather than relying on a live
join to SalaryRule) is what satisfies invariant 0.24: a later SalaryRule edit
must not change a previously computed Payslip.

## PayrollWarning
| Field | Type | Notes |
|---|---|---|
| id | uuid | PK |
| payrun_id | uuid FK -> Payrun, nullable | |
| payslip_id | uuid FK -> Payslip, nullable | |
| severity | enum(INFO, WARNING, ERROR) | |
| code | string | e.g. `MISSING_BANK_DETAILS` |
| message | string | |
| blocks_validation | boolean | derived from severity, stored for query simplicity |

## Key Relationships Summary

- Employee 1—* Contract, 1—* Attendance, 1—* TimeOffRequest, 1—* TimeOffAllocation, 1—* Payslip
- Employee *—1 Department, *—1 JobPosition, *—1 WorkingSchedule, *—0..1 Manager(Employee)
- WorkingSchedule 1—* WorkingScheduleLine
- SalaryStructure *—* SalaryRule via SalaryStructureRule (ordered)
- Payrun 1—* Payslip; Payslip 1—* PayslipLine
- Contract *—1 SalaryStructure (a contract states which structure applies to that employee for that period)
- Payrun *—1 SalaryStructure (chosen at Step 1; must be consistent with/override contract's structure — flagged as an open validation question if they differ, see PAYROLL_ENGINE.md)

## Archival / Deletion Policy

| Entity | On "delete" |
|---|---|
| Employee, Department, JobPosition, WorkingSchedule, SalaryStructure, SalaryRule, TimeOffType | set `active = false`; never hard-deleted once referenced by any historical record |
| Contract | never deleted; status becomes `EXPIRED`/`TERMINATED` |
| Payrun / Payslip / PayslipLine | never deleted once `COMPUTED` or later; `DRAFT` payruns may be hard-deleted/cancelled before compute |
| Attendance / TimeOffRequest / TimeOffAllocation | never hard-deleted; cancellation via status field |
