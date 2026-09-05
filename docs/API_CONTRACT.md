# API CONTRACT — PeoplePay360

**This is the integration boundary between Claude (backend/system-of-truth)
and Antigravity (frontend).** Claude owns and maintains this document. Any
backend change that adds/renames/reshapes an endpoint or an enum value must be
reflected here in the same change — this file, not the frontend's mock data,
is the source of truth for shape and vocabulary.

Status: **Planning only — nothing below is implemented yet.** This document
supersedes `API_PLAN.md`'s endpoint list with concrete request/response
shapes; `API_PLAN.md` remains the quick-reference index by module.

All endpoints: `/api/v1/...`, JSON, `Authorization: Bearer <JWT>`. Every
mutating endpoint re-checks the role server-side regardless of what the
frontend does or doesn't render (see `REQUIREMENTS.md` permission matrix).

---

## 1. Canonical Enums (Single Source of Truth)

Both agents use these exact strings. Neither agent invents a synonym.

```
UserRole:                  EMPLOYEE | HR_MANAGER | HR_PAYROLL_USER | HR_PAYROLL_MANAGER | ADMIN
EmployeeActiveStatus:      ACTIVE | INACTIVE
EmployeeType:              FULL_TIME | PART_TIME | CONTRACTOR
ContractStatus:            DRAFT | ACTIVE | EXPIRED | TERMINATED
WorkingScheduleType:       FULL_TIME | PART_TIME
DayOfWeek:                 MON | TUE | WED | THU | FRI | SAT | SUN
AttendanceStatus:          PRESENT | LATE | ABSENT | OVERTIME | MISSING_CHECK_OUT
TimeOffUnit:                DAYS | HOURS
TimeOffPayrollIntegration: NONE | UNPAID_DEDUCTION | PAID
AllocationStatus:          DRAFT | PENDING | APPROVED | REFUSED
TimeOffRequestStatus:      PENDING | APPROVED | REFUSED | CANCELLED
SalaryRuleCategory:        BASIC | ALLOWANCE | GROSS | DEDUCTION | NET
SalaryRuleComputationType: FIXED | PERCENTAGE | FORMULA
PayrunStatus:              DRAFT | COMPUTED | VALIDATED | PAID | CANCELLED
PayslipStatus:             DRAFT | COMPUTED | VALIDATED | PAID | CANCELLED
PayrollWarningSeverity:    INFO | WARNING | ERROR
```

Full field-level definitions for each entity are in `DATABASE_SCHEMA.md`;
this list exists so the frontend can hardcode dropdown options, badge colors,
and status-guard logic against exact strings instead of guessing.

## 2. Common Shapes

**Error envelope** (any 4xx/5xx):
```json
{
  "error": {
    "code": "NO_APPLICABLE_CONTRACT",
    "message": "No contract covers this payroll period",
    "details": {}
  }
}
```

**List envelope** (any collection GET):
```json
{
  "data": [ /* items */ ],
  "page": 1,
  "pageSize": 25,
  "total": 137
}
```

**PayrollWarning shape** (reused across Payrun/Payslip/Preflight responses):
```json
{
  "code": "MISSING_BANK_DETAILS",
  "severity": "WARNING",
  "message": "Employee is missing bank account details",
  "blocksValidation": false,
  "employeeId": "uuid",
  "payslipId": "uuid"
}
```

---

## 3. Auth

### POST /auth/login
Request: `{ "email": "string", "password": "string" }`
Response 200:
```json
{ "token": "jwt", "user": { "id": "uuid", "email": "string", "role": "UserRole", "employeeId": "uuid|null" } }
```
Errors: 401 `INVALID_CREDENTIALS`.

### GET /auth/me
Response 200: same `user` shape as above. Role: authenticated.

---

## 4. Employees

Standard CRUD shape mirrors the Employee fields in `DATABASE_SCHEMA.md`
(`employeeNumber, firstName, lastName, email, phone, departmentId, managerId,
jobPositionId, employeeType, workingScheduleId, bankDetails, activeStatus,
joinDate`). List supports `?department=&type=&status=&search=`.

`GET /employees/:id` response additionally nests summary counts for the hub
(not full sub-lists — those are separate calls):
```json
{
  "id": "uuid", "employeeNumber": "EMP-1001", "firstName": "Arjun", "lastName": "Mehta",
  "department": { "id": "uuid", "name": "Engineering" },
  "manager": { "id": "uuid", "firstName": "Priya", "lastName": "Sharma" },
  "jobPosition": { "id": "uuid", "title": "Software Engineer" },
  "workingSchedule": { "id": "uuid", "name": "Standard 5-Day", "weeklyHours": 37.5 },
  "activeStatus": "ACTIVE",
  "hasBankDetails": true,
  "activeContractId": "uuid|null"
}
```
Sub-resources: `GET /employees/:id/contracts`, `/attendance`, `/time-off`,
`/payslips`, `/leave-balance` — each a list envelope of that module's shape.

Role: `HR_MANAGER+` for CRUD and any-employee reads; `EMPLOYEE` may read only
where `:id` resolves to their own linked `employeeId`.

---

## 5. Contracts

Fields per `DATABASE_SCHEMA.md`: `employeeId, startDate, endDate, wage,
departmentId, jobPositionId, salaryStructureId, status`.

`POST /contracts` creates a new historical row (never overwrites); if it
overlaps an existing `ACTIVE` contract for the same employee, the response is
`409 CONFLICTING_CONTRACT` with the conflicting contract's id in `details` —
the caller (HR) must explicitly terminate/expire the old one first, this is
never auto-resolved silently.

`POST /contracts/:id/terminate` → status `TERMINATED`, requires `endDate`.

Role: `HR_MANAGER+`.

---

## 6. Working Schedules

```json
{
  "id": "uuid", "name": "Standard 5-Day", "type": "FULL_TIME",
  "lines": [
    { "dayOfWeek": "MON", "startTime": "09:00", "endTime": "17:00", "breakDurationMinutes": 30 }
  ],
  "weeklyHours": 37.5
}
```
`weeklyHours` is **server-computed on every read**, never accepted on write —
POST/PUT only accept `name`, `type`, `lines`. Invalid lines (`endTime <=
startTime`, negative break) return `422 INVALID_SCHEDULE_LINE`.

Role: `HR_MANAGER+`.

---

## 7. Attendance

```json
{
  "id": "uuid", "employeeId": "uuid", "date": "2026-08-10",
  "checkIn": "2026-08-10T09:05:00Z", "checkOut": "2026-08-10T17:10:00Z",
  "workedHours": 7.75, "status": "LATE",
  "manuallyEdited": false, "correctedBy": null, "correctedAt": null, "correctionReason": null
}
```
`POST /attendance/check-in` — self or HR, body `{}` (server stamps time).
`POST /attendance/:id/check-out` — same.
`PUT /attendance/:id` — HR only; body may set `checkIn`/`checkOut` plus
required `correctionReason`; server recomputes `workedHours`/`status` and
stamps `manuallyEdited/correctedBy/correctedAt`.

Role: `HR_MANAGER+` for any-employee and corrections; `EMPLOYEE` self check-in/out only.

---

## 8. Time Off

**TimeOffType**: `{ id, name, unit: TimeOffUnit, requiresAllocation, requiresApproval, payrollIntegration, active }`

**TimeOffAllocation**: `{ id, employeeId, timeOffTypeId, allocatedAmount, validityStart, validityEnd, status }`

`GET /employees/:id/leave-balance?timeOffTypeId=` →
```json
{ "timeOffTypeId": "uuid", "allocated": 18, "taken": 4, "remaining": 14 }
```
All three numbers are server-derived per `LEAVE_RULES.md`; never accept a
client-supplied `remaining`.

**TimeOffRequest**: `{ id, employeeId, timeOffTypeId, startDate, endDate, duration, status, decidedBy, decidedAt }`

`POST /time-off-requests/:id/approve`:
Response 200 on success; `409 INSUFFICIENT_BALANCE` if `requiresAllocation`
and `duration > remaining`; `409 INVALID_STATE` if request is not `PENDING`
(idempotency guard per `LEAVE_RULES.md` — a duplicate approve call is
rejected, not silently re-applied).

Role: read/create-own `EMPLOYEE`; configure/approve/refuse `HR_MANAGER+`.

---

## 9. Salary Structures & Salary Rules

**SalaryRule**: `{ id, name, code, category: SalaryRuleCategory, sequence,
computationType: SalaryRuleComputationType, valueConfig, active }`

`valueConfig` shape depends on `computationType` (see `SALARY_RULE_ENGINE.md`):
```json
// FIXED
{ "amount": 30000, "prorate": true }
// PERCENTAGE
{ "percentOf": "BASIC", "percent": 40 }
// FORMULA
{ "expression": "BASIC + HRA + TRANSPORT" }
```

`POST/PUT /salary-structures/:id` body includes an ordered `rules: [{
salaryRuleId, sequence }]` array. Server validates (per
`SALARY_RULE_ENGINE.md`) that every `percentOf`/formula identifier resolves to
a rule at a strictly lower `sequence` in the same structure; violations return
`422 INVALID_RULE_REFERENCE` naming the offending rule and identifier —
never silently accepted.

Role: read `HR_PAYROLL_USER+`; write `HR_PAYROLL_MANAGER+`.

---

## 10. Payruns (Two-Step Creation + State Machine)

### POST /payruns/eligible-employees  (Step 1 → 2, no Payrun created)
Request: `{ "salaryStructureId": "uuid", "periodStart": "2026-08-01", "periodEnd": "2026-08-31" }`
Response 200:
```json
{
  "eligible": [
    { "employeeId": "uuid", "name": "Arjun Mehta", "department": "Engineering", "contractId": "uuid" }
  ],
  "excluded": [
    { "employeeId": "uuid", "name": "...", "reason": "NO_APPLICABLE_CONTRACT" }
  ]
}
```

### POST /payruns  (Step 2 submit → creates DRAFT Payrun)
Request: `{ "salaryStructureId": "uuid", "periodStart": "...", "periodEnd": "...", "employeeIds": ["uuid", ...] }`
Response 201: Payrun object, `status: "DRAFT"`, no payslips yet.

### GET /payruns, GET /payruns/:id
```json
{
  "id": "uuid", "reference": "PAYRUN-2026-08", "salaryStructureId": "uuid",
  "periodStart": "2026-08-01", "periodEnd": "2026-08-31",
  "status": "COMPUTED", "employeeCount": 10,
  "createdBy": "uuid", "createdAt": "..."
}
```

### POST /payruns/:id/compute
Idempotent — safe to call repeatedly (updates existing Payslips in place,
never duplicates; see `PAYRUN_STATE_MACHINE.md`). Response 200:
```json
{
  "id": "uuid", "status": "COMPUTED",
  "summary": { "employeeCount": 10, "totalGross": 500000, "totalDeductions": 50000, "totalNet": 450000 },
  "payslips": [ { "id": "uuid", "employeeId": "uuid", "status": "COMPUTED", "net": 45000 } ],
  "warnings": [ /* PayrollWarning[] */ ]
}
```
Errors: `409 INVALID_STATE` if `status` is `VALIDATED`, `PAID`, or `CANCELLED`.

### POST /payruns/:id/validate
Errors: `422 VALIDATION_BLOCKED` with `{ "warnings": [...] }` (only `ERROR`
severity ones) if any blocking warning remains; `409 INVALID_STATE` if not
`COMPUTED`. Response 200 on success: Payrun with `status: "VALIDATED"`.

### POST /payruns/:id/mark-paid
Errors: `409 INVALID_STATE` if not `VALIDATED`; `422 MISSING_BANK_DETAILS` if
any member payslip's employee lacks bank details. Response 200: `status: "PAID"`.

### POST /payruns/:id/send-payslips
Fire-and-forget relative to payroll state — never changes Payrun/Payslip
status or numbers. Response 202:
```json
{ "queued": 10, "failed": 0 }
```

### POST /payruns/:id/cancel
Only from `DRAFT`/`COMPUTED`. Role: `HR_PAYROLL_MANAGER+`.

All Payrun mutating endpoints: role `HR_PAYROLL_USER+` unless noted.

---

## 11. Payslips

```json
{
  "id": "uuid", "payrunId": "uuid", "employeeId": "uuid", "contractId": "uuid",
  "salaryStructureId": "uuid", "periodStart": "...", "periodEnd": "...",
  "workedDays": 22, "status": "VALIDATED",
  "lines": [
    { "ruleCode": "BASIC", "category": "BASIC", "sequence": 10, "amount": 30000 },
    { "ruleCode": "HRA", "category": "ALLOWANCE", "sequence": 20, "amount": 12000 },
    { "ruleCode": "NET", "category": "NET", "sequence": 70, "amount": 39100 }
  ],
  "warnings": [ /* PayrollWarning[] */ ]
}
```
`GET /payslips/:id/pdf` → `200`, `Content-Type: application/pdf`.

Role: `HR_PAYROLL_USER+`; `EMPLOYEE` may `GET` only their own, read-only.

---

## 12. Innovation Layer

Reuses `payroll/ruleEngine.ts` and `payroll/contractSelection.ts` directly —
none of the three below re-implements calculation logic (see
`PAYROLL_ENGINE.md` §Innovation Layer).

### 12.1 PayTrace — `GET /payslips/:id/trace`
Explains how each line was derived, in execution order, using the same
`context.results` object the rule engine already produces (no recomputation
of unrelated logic):
```json
{
  "payslipId": "uuid",
  "steps": [
    { "sequence": 10, "ruleCode": "BASIC", "computationType": "FIXED", "inputs": { "contractWage": 30000, "workedDays": 22, "expectedDays": 22 }, "amount": 30000 },
    { "sequence": 20, "ruleCode": "HRA", "computationType": "PERCENTAGE", "inputs": { "percentOf": "BASIC", "percent": 40, "baseAmount": 30000 }, "amount": 12000 },
    { "sequence": 40, "ruleCode": "GROSS", "computationType": "FORMULA", "inputs": { "expression": "BASIC + HRA + TRANSPORT", "resolved": { "BASIC": 30000, "HRA": 12000, "TRANSPORT": 2000 } }, "amount": 44000 }
  ]
}
```
Role: same as reading the underlying Payslip.

### 12.2 Payroll Preflight — `GET /payruns/:id/preflight`
Runs `validatePayslip`/the Validation Matrix (`PAYROLL_ENGINE.md` §I) against
the Payrun's current (possibly not-yet-computed) selection **without**
mutating state — safe to call from `DRAFT` onward, before or after Compute:
```json
{
  "payrunId": "uuid",
  "blockers": [ { "code": "NO_APPLICABLE_CONTRACT", "employeeId": "uuid", "message": "..." } ],
  "warnings": [ { "code": "MISSING_BANK_DETAILS", "employeeId": "uuid", "message": "..." } ],
  "canValidate": false
}
```
Every entry must trace to an actual check in `validation.ts` — no
placeholder/fake warnings ever. Role: `HR_PAYROLL_USER+`.

### 12.3 Payroll Simulator — `POST /payruns/:id/simulate`
Request: a **hypothetical** salary structure/rule override, never touching
stored data:
```json
{
  "salaryStructureId": "uuid",
  "ruleOverrides": [ { "salaryRuleId": "uuid", "valueConfig": { "percent": 45 } } ]
}
```
Server runs the real rule engine (`ruleEngine.ts`) against an in-memory copy
of the structure/rules with overrides applied, for the Payrun's already-
selected employees and contracts — no `SalaryRule`, `Payslip`, `Payrun`, or
`Contract` row is written. Response 200: same `summary`/`payslips` shape as
`/compute`, plus a diff against the last real computation:
```json
{
  "summary": { "totalNet": 462000 },
  "diffFromActual": { "totalNet": 12000 },
  "payslips": [ { "employeeId": "uuid", "net": 46200, "netDelta": 1200 } ]
}
```
Role: `HR_PAYROLL_MANAGER+` (touches hypothetical rule configuration, kept at
the same permission level as real rule editing).

---

## 13. Dashboard

`GET /dashboard/summary?period=&department=&employeeType=`:
```json
{
  "totalNetPaid": 4500000, "payslipsGenerated": 100, "averageSalary": 45000,
  "approvedTimeOff": 23, "attendanceHealth": { "presentRate": 0.94, "lateRate": 0.03, "absentRate": 0.02, "missingCheckOutRate": 0.01 }
}
```
`GET /dashboard/salary-by-department`, `GET /dashboard/monthly-net-trend` —
chart-ready arrays. `GET /dashboard/operational-flags` — duplicate payslips,
contract issues, missing data, attendance exceptions, each item carrying an
`employeeId`/`payrunId` so the frontend can deep-link.

All dashboard values are computed from live rows at request time — no
precomputed/cached snapshot table backs these endpoints in MVP. Role:
`HR_PAYROLL_USER+`.

---

## 14. Admin

Standard CRUD on `/users` — `{ email, role, employeeId, active }`. Role: `ADMIN`.

---

## 15. Change Log

| Date | Change |
|---|---|
| 2026-09-05 | Initial contract drafted alongside Phase 0 docs; includes PayTrace/Preflight/Simulator per parallel-development context |

Every future change to this file must append a row here so Antigravity can
tell, at a glance, whether their local copy of the contract is current.
