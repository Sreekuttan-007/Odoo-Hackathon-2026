# Build Status

Track module implementation state here.

- **Frontend App Shell**: DONE
- **Backend API Foundation**: DONE
- **Database/Migrations**: DONE
- **Authentication**: DONE
- **User Management**: DONE
- **Employee Management**: DONE (Kanban + List, detail, create/edit, Department/Job Position/Manager/Working Schedule relations, RBAC)
- **Departments**: DONE (minimal CRUD + reusable selector + seed data)
- **Job Positions**: DONE (minimal CRUD + reusable selector + seed data, no dedicated nav page — managed inline via selector "create" action)
- **Contracts**: DONE (list/detail/create, history, overlap validation, period-applicability service, money-safe wage)
- **Working Schedules**: DONE (list/form, weekly pattern lines, derived daily/weekly hours)
- **Attendance**: DONE (global + employee-filtered list, detail, quick Check In/Check Out widget with live elapsed display, HR correction, real derived worked-hours/overtime, one-session/day + overlap protection)
- **Time Off**: DONE (Types configuration, Allocations with approve/refuse and derived balance, Requests with approve/refuse and exactly-once balance consumption, employee-filtered smart action, real RBAC)
- **Salary Structures/Rules**: DONE (ordered rules, FIXED/PERCENTAGE/FORMULA computation via a safe AST-based evaluator, RBAC split between HR_PAYROLL_USER read-only and HR_PAYROLL_MANAGER full CRUD)
- **Payruns/Payslips**: DONE (two-step creation wizard with backend-revalidated eligibility, DRAFT→COMPUTED→VALIDATED→PAID state machine, real preflight blockers/warnings, PayslipLine computation trace, historically-stable snapshots, real PDF generation)
