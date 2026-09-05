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
