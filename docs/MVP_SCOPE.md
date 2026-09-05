# MVP SCOPE — PeoplePay360

## P0 — Must Work (Intellectual Core)

- Employee Management: records, List/Form (Kanban is P1 polish of an existing List), employee hub
- Contracts: history, period-specific selection (`getApplicableContract`), conflict handling
- Working Schedules: weekly pattern, derived weekly hours
- Attendance: check-in/out, derived worked hours, basic exception statuses
- Time Off: Types, Allocations, Requests, Approve/Refuse, derived balance
- Payroll Configuration: Salary Structures, Salary Rules, sequencing, real computation (FIXED/PERCENTAGE/FORMULA)
- Payroll: two-step Payrun creation, eligibility, Compute, validation warnings, Validate, Mark Paid, Payslip breakdown

## P1 — Required to Finish the Full PS

- Role-based permissions (all 5 roles enforced server-side)
- Payroll Dashboard (live-data aggregation)
- PDF Payslips
- Bulk email distribution (Send Payslips)
- Historical Payruns (browse past, re-open computed data)
- Filters (period/department/employee type) across list and dashboard views

## P2 — Polish Only If Time Remains

- Advanced Kanban polish for Employees
- Advanced charts (beyond the two specified: salary-by-department, monthly net trend)
- Elaborate attendance scoring
- Detailed email templates
- Exports (CSV/Excel)
- Animations
- Enhanced search
- Extra dashboard widgets

## Do Not Build (Explicitly Out of Scope)

Recruitment/ATS, performance reviews, expense reimbursement, employee chat, AI
chatbot, biometric/facial/GPS attendance, tax filing, advanced statutory
payroll compliance, real banking/bank API integration, accounting/ERP
integration, multi-company, international payroll, multi-currency,
microservices, Kafka, Redis (unless a real need emerges), Kubernetes,
blockchain, ML salary prediction.

## Sequencing Note

P0 items are not independently orderable — Contracts/Schedules must exist
before Attendance is meaningful, Attendance/Leave must exist before payroll
worked-days math is meaningful, and Salary Rules must exist before a Payrun
can compute anything. See CLAUDE.md's Phase Plan for the concrete build order
(Phase 1 → Phase 12).
