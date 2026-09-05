# Phase Log

## Phase 0: Project Foundation Restart
- **Status**: DONE
- **Requirements**: Initialize React frontend, FastAPI backend, base project documentation, App Shell placeholder, backend `/api/health`, Alembic migrations base.
- **Deferred**: No actual payroll calculations or UI flows implemented yet.

## Phase 1: Authentication & User Management
- **Status**: DONE
- **Requirements**: JWT login, `/auth/me`, RBAC roles, Admin user management (create/deactivate), Employee base model.

## Phase 2: Employee, Contract & Working Schedule Flow
- **Status**: DONE
- **Requirements**: Employee Kanban + List + detail (Department/Job Position/Manager/Working Schedule relations, RBAC-gated create/edit), Department and Job Position minimal models + reusable selectors, Contract model with history/overlap protection/period-applicability service and money-safe wage, Working Schedule + weekly pattern lines with derived daily/weekly hours, real APIs/persistence/validation/tests for all of the above.
- **Business logic**: `app/services/contract_rules.py` (overlap validation, period applicability, reference generation, derived status) and `app/services/schedule_calculator.py` (derived hours) — both unit-tested independent of the API layer.
- **Migration**: `e8ac28b2eaef_phase2_employee_contract_working_.py` adds `departments`, `job_positions`, `working_schedules`, `working_schedule_lines`, `contracts`, and extends `employees` with `employee_code`, `work_location`, `status`, `department_id`, `job_position_id`, `manager_id`, `working_schedule_id` (dropping the old free-text `department` column).
- **Deferred**: Attendance, Time Off, Allocations, Salary Structure/Rules, Payrun/Payslip computation — not started, no placeholder data fabricated for their counts.

## UI Recovery Pass
- **Status**: DONE
- **Requirements**: Visual-system refactor only — no backend/API/schema changes. Repurposed the brand accent to a deliberate indigo and remapped Tailwind's gray scale to warm-neutral; added shared primitives (Button, PageHeader, EmptyState, Skeleton, SectionCard, DetailField, Drawer, single StatusBadge); rebuilt App Shell, Login, Employees, Employee Detail, Contracts, Contract Detail, Working Schedules, and User Management on top of them; converted form modals to slide-in drawers; wired the previously-dead User Management "Edit" action to the existing `PATCH /admin/users` endpoint.

## Phase 3: Attendance Flow
- **Status**: DONE
- **Requirements**: Global + Employee-filtered Attendance list, Attendance detail, quick Check In/Check Out widget (topbar) with live elapsed display, HR-authorized corrections, real derived worked-hours/overtime, one-open-session + one-record-per-day + overlap protection, RBAC.
- **Business logic**: `app/services/attendance_rules.py` — check-in/check-out state transitions, derived `worked_minutes`/status/overtime, overlap detection, and the UTC/company-timezone normalization needed because SQLite drops `tzinfo` on round-trip (`as_utc()`). Unit- and API-tested (`tests/test_attendance_rules.py`, `tests/test_attendance_api.py`).
- **Migration**: `a178d4185523_phase3_attendance.py` adds `attendances` (`employee_id`, `attendance_date`, `check_in`, `check_out`, `notes`, `corrected_by_user_id`, timestamps). `Employee` responses now also carry a real `attendance_count`.
- **Deferred**: Time Off, Allocations, Salary Structure/Rules, Payrun/Payslip, dashboard analytics, biometric/GPS/geofencing — not started, no placeholder data fabricated.

## Phase 4: Time Off Flow
- **Status**: DONE
- **Requirements**: Time Off Types (configuration: unit, requires-allocation, approval policy, active/inactive, display color), Allocations (Allocated/Taken/Remaining list + detail, approve/refuse), Time Off Requests (create, approve, refuse, employee/type-filtered list, detail with balance breakdown), employee-filtered smart action with a real count, balance-preview endpoint for the request form.
- **Business logic**: `app/services/time_off_rules.py` — duration computation from the employee's Working Schedule (DAYS = scheduled working-day count with a documented calendar-day fallback when no schedule exists; HOURS = sum of scheduled days' expected hours, rejected outright without a schedule), allocation resolution/uniqueness, the exactly-once balance consumption rule (`taken` = live sum of APPROVED requests linked to an allocation, never persisted), the approve/refuse state machine with self-approval blocking. Unit- and API-tested (`tests/test_time_off_rules.py`, `tests/test_time_off_api.py`), including the spec's canonical balance test (20 allocated / 5 pre-approved / 15 remaining -> approve a 3-day request -> 12 remaining -> re-approving rejected, not double-deducted).
- **Migration**: `202e969ce549_phase4_time_off.py` adds `time_off_types`, `time_off_allocations`, `time_off_requests`. `Employee` responses now also carry a real `time_off_requests_count`.
- **Deferred**: "My Team" filtering (manager hierarchy not reliable enough yet — not faked), a Time Off dashboard, multi-level/manager-routed approvals (approval is HR-capable-role + never-self, not yet resolved via `Employee.manager`), accrual automation, carry-forward, public holidays, and any Attendance/Payroll integration from approved leave — not started, no placeholder data fabricated.

## Phase 5: Payroll Engine (Salary Structures, Rules, Payruns & Payslips)
- **Status**: DONE
- **Requirements**: Salary Structures (ordered Salary Rules), Salary Rules (FIXED/PERCENTAGE/FORMULA computation, category BASIC/ALLOWANCE/GROSS/DEDUCTION/NET), a two-step Payrun creation wizard (scope → backend-revalidated employee selection, "Continue" never persists), the DRAFT→COMPUTED→VALIDATED→PAID state machine, real payroll preflight blockers/warnings, Payslips with a full rule-by-rule PayslipLine computation trace, and real PDF generation.
- **Business logic**: `app/services/formula_engine.py` (a constrained AST-based expression evaluator — no `eval`/`exec`, no attribute access, calls, or imports; whitelists arithmetic and `rules["CODE"]`/`categories["CATEGORY"]` subscripts) and `app/services/payroll_engine.py` (eligibility resolution reusing Phase 2's `getApplicableContract`, the sequence-ordered rule execution engine, the state machine, and historical-snapshot integrity). Unit- and API-tested (`tests/test_formula_engine.py`, `tests/test_payroll_engine.py`, `tests/test_payroll_api.py`), including the spec's own canonical worked example (Contract Wage ₹50,000 → Basic ₹25,000 → HRA ₹5,000 → Gross ₹32,000 → PF ₹2,500 → Net ₹29,500) and a historical-integrity test proving a PAID Payslip's numbers don't change after its Salary Rule is edited afterward.
- **Migration**: `263963d3918b_phase5_payroll.py` adds `salary_structures`, `salary_rules` (unique per structure+code), `payruns`, `payslips` (unique per payrun+employee), `payslip_lines`, `payroll_warnings`.
- **RBAC**: new `get_current_payroll_operator` (`HR_PAYROLL_USER`/`HR_PAYROLL_MANAGER`/`ADMIN` — Payrun/Payslip operations) and `get_current_payroll_manager` (`HR_PAYROLL_MANAGER`/`ADMIN` only — Salary Structure/Rule configuration) added to `app/api/deps.py`. `HR_MANAGER` has no payroll access at all, matching the spec exactly.
- **PDF**: real `reportlab`-generated PDFs from persisted, already-computed Payslip data (never recomputed) — see `app/services/payslip_pdf.py`.
- **Deferred (explicitly, per spec)**: "Send Payslips" (no email provider configured in this environment — not faked), a Payroll Dashboard (next phase), mid-period contract-change proration, a paid/unpaid leave distinction (TimeOffType has no such flag yet — `approved_leave_days` context is exposed but unused by the seeded rules), and any statutory/compliance claim (PF/PT rules are calculation examples only).
