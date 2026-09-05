# API PLAN — PeoplePay360 (Planning Only — Not Implemented)

All endpoints are `/api/v1/...`, JSON, JWT bearer auth. Role required is
listed per endpoint (see REQUIREMENTS.md permission matrix). Every mutating
endpoint re-validates role server-side regardless of what the frontend shows.

## Auth
| Method | Path | Purpose | Role |
|---|---|---|---|
| POST | /auth/login | issue JWT | any |
| POST | /auth/logout | invalidate client session | authenticated |
| GET | /auth/me | current user + role + linked employee | authenticated |

## Employees
| Method | Path | Purpose | Role |
|---|---|---|---|
| GET | /employees | list/search/filter (dept, type, status) | HR_MANAGER+ |
| GET | /employees/:id | employee hub detail | HR_MANAGER+ (self for EMPLOYEE) |
| POST | /employees | create | HR_MANAGER+ |
| PUT | /employees/:id | update | HR_MANAGER+ |
| GET | /employees/:id/contracts | linked contracts | HR_MANAGER+ (self) |
| GET | /employees/:id/attendance | linked attendance | HR_MANAGER+ (self) |
| GET | /employees/:id/time-off | linked requests/allocations | HR_MANAGER+ (self) |
| GET | /employees/:id/payslips | linked payslips | HR_PAYROLL_USER+ (self) |
| GET | /departments, /job-positions | lookups | HR_MANAGER+ (read for all authenticated for dropdowns) |

## Contracts
| Method | Path | Purpose | Role |
|---|---|---|---|
| GET | /contracts | list (filter by employee) | HR_MANAGER+ |
| POST | /contracts | create (new historical contract) | HR_MANAGER+ |
| PUT | /contracts/:id | update (only if DRAFT; else restricted) | HR_MANAGER+ |
| POST | /contracts/:id/terminate | status -> TERMINATED | HR_MANAGER+ |

## Working Schedules
| Method | Path | Purpose | Role |
|---|---|---|---|
| GET | /working-schedules | list | HR_MANAGER+ |
| POST | /working-schedules | create with lines | HR_MANAGER+ |
| PUT | /working-schedules/:id | update lines, recompute weekly hours | HR_MANAGER+ |

## Attendance
| Method | Path | Purpose | Role |
|---|---|---|---|
| GET | /attendance | list/filter (employee, date range, status) | HR_MANAGER+ (self for EMPLOYEE) |
| POST | /attendance/check-in | create today's record | EMPLOYEE (self) or HR_MANAGER+ |
| POST | /attendance/:id/check-out | close today's record | EMPLOYEE (self) or HR_MANAGER+ |
| PUT | /attendance/:id | correction (sets manually_edited metadata) | HR_MANAGER+ |

## Time Off
| Method | Path | Purpose | Role |
|---|---|---|---|
| GET | /time-off-types | list | all authenticated (read) |
| POST/PUT | /time-off-types(/:id) | configure | HR_MANAGER+ |
| GET | /time-off-allocations | list/filter | HR_MANAGER+ (self for EMPLOYEE) |
| POST | /time-off-allocations | grant allocation | HR_MANAGER+ |
| GET | /time-off-requests | list/filter | HR_MANAGER+ (self for EMPLOYEE) |
| POST | /time-off-requests | create own request | EMPLOYEE (self), HR_MANAGER+ (any) |
| POST | /time-off-requests/:id/approve | approve, consume allocation | HR_MANAGER+ |
| POST | /time-off-requests/:id/refuse | refuse | HR_MANAGER+ |
| GET | /employees/:id/leave-balance | derived allocated/taken/remaining | HR_MANAGER+ (self) |

## Salary Structures
| Method | Path | Purpose | Role |
|---|---|---|---|
| GET | /salary-structures | list | HR_PAYROLL_USER+ (read) |
| POST/PUT | /salary-structures(/:id) | manage + attach rules with sequence | HR_PAYROLL_MANAGER+ |

## Salary Rules
| Method | Path | Purpose | Role |
|---|---|---|---|
| GET | /salary-rules | list | HR_PAYROLL_USER+ (read) |
| POST/PUT | /salary-rules(/:id) | manage, validate config on save | HR_PAYROLL_MANAGER+ |

## Payruns
| Method | Path | Purpose | Role |
|---|---|---|---|
| POST | /payruns/eligible-employees | Step 1->2: given structure+period, return eligible employees | HR_PAYROLL_USER+ |
| POST | /payruns | Step 2 submit: create Payrun with selected employees | HR_PAYROLL_USER+ |
| GET | /payruns, /payruns/:id | list/detail | HR_PAYROLL_USER+ |
| POST | /payruns/:id/compute | run/re-run computation | HR_PAYROLL_USER+ |
| POST | /payruns/:id/validate | validate (blocked by ERROR warnings) | HR_PAYROLL_USER+ |
| POST | /payruns/:id/mark-paid | status -> PAID | HR_PAYROLL_USER+ |
| POST | /payruns/:id/send-payslips | trigger email delivery | HR_PAYROLL_USER+ |
| POST | /payruns/:id/cancel | DRAFT/COMPUTED -> CANCELLED | HR_PAYROLL_MANAGER+ |

## Payslips
| Method | Path | Purpose | Role |
|---|---|---|---|
| GET | /payslips, /payslips/:id | list/detail incl. lines + warnings | HR_PAYROLL_USER+ (self, read-only, for EMPLOYEE) |
| GET | /payslips/:id/pdf | generate/download PDF | HR_PAYROLL_USER+ (self for EMPLOYEE) |

## Dashboard
| Method | Path | Purpose | Role |
|---|---|---|---|
| GET | /dashboard/summary | net paid, payslip count, avg salary, approved time off, attendance health | HR_PAYROLL_USER+ |
| GET | /dashboard/salary-by-department | chart data | HR_PAYROLL_USER+ |
| GET | /dashboard/monthly-net-trend | chart data | HR_PAYROLL_USER+ |
| GET | /dashboard/operational-flags | duplicate payslips, contract issues, missing data, attendance exceptions | HR_PAYROLL_USER+ |

Query params `period`, `department`, `employeeType` apply as filters across
dashboard endpoints, always resolved against real rows at request time — never
cached/precomputed static values.

## Admin
| Method | Path | Purpose | Role |
|---|---|---|---|
| GET/POST/PUT | /users(/:id) | user + role management | ADMIN |
