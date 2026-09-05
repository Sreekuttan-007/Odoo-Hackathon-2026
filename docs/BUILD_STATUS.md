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
- **Phase 7 — PayTrace**: DONE (deterministic per-payslip calculation explainer at `/payroll/payslips/:id/trace`, rebuilt entirely from persisted PayslipLine snapshots — verified historically stable against later Salary Rule edits; graceful fallback for pre-Phase-7 legacy lines). **AI Narrator (7B)**: implemented but unconfigured in this environment (`ANTHROPIC_API_KEY` unset) — endpoint verified to degrade to `available: false` rather than fail; untested against a live provider response.
- **Phase 8 — Payroll Preflight**: DONE (deterministic payroll readiness & risk engine, `app/services/preflight.py`). Derived — persists nothing, adds no Payrun status. `GET`/`POST /api/payroll/payruns/:id/preflight` returns `readiness` (NOT_RUN / ACTION_REQUIRED / REVIEW_RECOMMENDED / READY), severity counts, and normalized findings. 13 registered checks across contract / config / integrity / attendance / time-off / variance / duplicates dimensions, reusing the canonical contract-applicability + overlap rules and bridging the compute engine's own BLOCKER `PayrollWarning`s. **Validation gate**: `validate_payrun` recomputes every Payslip then re-runs the Preflight engine server-side and refuses (`409 VALIDATION_BLOCKED`, now with `details.findings`) on any blocker — a stale UI "READY" cannot pass. Preflight panel on the Payrun detail page: readiness banner, blocker/warning/info counts, severity filters, per-finding evidence + resolution + deep links (employee / contracts / payslip / PayTrace), "Run again", and a disabled Validate button while blockers exist. No AI anywhere in the engine. Migration: none (fully derived).
