# ARCHITECTURE — PeoplePay360

## Layered Architecture

```
Frontend (React SPA)
        |
        v  REST/JSON, JWT bearer
API / Route layer (thin — auth check, input parsing, calls service, formats response)
        |
        v
Application / Domain Services (attendanceService, leaveService, contractService,
                                payrollService, dashboardService, ...)
        |
        v
Business Rule modules (contract-selection, rule-engine, payroll-calculation,
                        validation, payslip-generation)
        |
        v
Database (PostgreSQL via ORM)

Supporting, decoupled modules (called BY services, never contain business rules):
  - PDF service   (renders a Payslip -> PDF from already-computed data)
  - Email service (sends already-generated PDFs; failure here must not
                    corrupt or roll back payroll state)
```

Rule: **routes never contain business logic**, **components never compute
payroll**, **the database has no stored procedures encoding payroll math**.
Everything payroll-related is a plain, readable, testable function in a
service module.

## Stack Proposal

| Layer | Choice | Why this | Why not simpler/other |
|---|---|---|---|
| Language | TypeScript (frontend + backend) | One language across the stack speeds a small hackathon team up, and static types catch payroll-context shape bugs (e.g. passing the wrong contract) at compile time — valuable given how much of this app is data shape correctness. | Plain JS is "simpler" to start but removes exactly the safety net most useful for a calculation-heavy domain; not worth the tradeoff here. |
| Backend runtime/framework | Node.js + Express | Minimal, unopinionated, huge familiarity, trivial to reason about request→service call. No hidden magic (no decorators/DI containers to explain to judges). | NestJS offers more structure but adds metaprogramming/DI concepts the spec explicitly says to avoid ("avoid hidden framework magic"). Express keeps the API layer a thin, readable pass-through. |
| Database | PostgreSQL | Strong relational integrity (foreign keys, unique constraints) is exactly what protects the invariants that matter most here: no duplicate payslips (unique constraint), no orphaned payslip lines, contract history preserved. Native date-range operators help contract-overlap queries. | A NoSQL store would push referential integrity (duplicate prevention, cascade behavior) into application code — riskier for a system whose entire pitch is "connected modules," not "disconnected documents." |
| ORM / data access | Prisma | Schema-as-code doubles as living documentation of the ER model (directly matches DATABASE_SCHEMA.md), generates type-safe queries, migrations are explicit and reviewable. | Raw SQL is more "explicit" per the philosophy, but for a time-boxed hackathon the type-safety and migration ergonomics outweigh the marginal transparency loss; Prisma's generated queries remain simple to read and are not hidden behind hand-rolled query builders. |
| Auth | JWT (short-lived access token), role embedded in token + re-verified against DB on sensitive actions | Stateless, no session-store dependency (no Redis needed), simple to explain and demo. | Full session-store auth (Redis-backed) adds an infra dependency the spec says to avoid "unless proven necessary." |
| Frontend | React + TypeScript + Vite | Fast dev server, huge ecosystem for tables/forms/Kanban, easy to keep components dumb (pure rendering) with all logic in services/hooks that call the API. | A meta-framework (Next.js) adds SSR/routing complexity not needed for an internal business app with a plain SPA + REST API. |
| Styling | Tailwind CSS + a small component set (e.g. headless UI primitives) | Fast to build clean, professional business-software UI without hand-rolling CSS; avoids "gaming aesthetic" drift because utility classes default to plain, restrained styling. | A full design-system library (MUI, AntD) is heavier than needed and fights customization; Tailwind + a few primitives is the smallest set that still looks professional. |
| PDF generation | Server-side HTML→PDF (e.g. a lightweight headless-render library) invoked by a dedicated `pdfService`, given already-computed Payslip data | Keeps PDF rendering a pure function of already-correct data — it cannot influence payroll numbers. | Client-side PDF generation would require shipping payroll calculation trust to the browser; server-side keeps the single source of truth server-side. |
| Email delivery | A single, swappable `emailService` interface (e.g. SMTP or a transactional email API) called only from a `sendPayslips` workflow, never from `computePayrun` | Isolates a failure-prone I/O boundary from the payroll state machine — an email failure must never roll back a Payrun's computed/validated state. | Embedding email calls inside payroll computation would couple an unreliable network call to a critical, must-be-deterministic business operation. |

No microservices, no message queue, no Redis, no Kubernetes: single deployable
API + single SPA + single Postgres database is sufficient for the required
functionality and maximizes demo reliability.

## Proposed Backend Folder Structure

```
backend/
  src/
    api/                     # thin route handlers, per module
      auth.routes.ts
      employees.routes.ts
      contracts.routes.ts
      workingSchedules.routes.ts
      attendance.routes.ts
      timeOff.routes.ts
      salaryStructures.routes.ts
      salaryRules.routes.ts
      payruns.routes.ts
      payslips.routes.ts
      dashboard.routes.ts
    services/                # application/domain services
      employeeService.ts
      contractService.ts
      workingScheduleService.ts
      attendanceService.ts
      leaveService.ts
      salaryStructureService.ts
      payrollService.ts
      dashboardService.ts
    payroll/                 # dedicated payroll business modules (0.19)
      contractSelection.ts
      ruleEngine.ts
      payrollCalculation.ts
      validation.ts
      payslipGeneration.ts
    integrations/
      pdfService.ts
      emailService.ts
    auth/
      jwt.ts
      permissions.ts         # role -> allowed-action checks, used by services
    db/
      schema.prisma
      client.ts
    middleware/
      requireAuth.ts
      requireRole.ts
    types/
    utils/
  tests/
    unit/
    integration/
```

## Proposed Frontend Folder Structure

```
frontend/
  src/
    pages/
      Dashboard/
      Employees/ (List, Kanban, Form, hub tabs: Contracts/Attendance/TimeOff/Payslips)
      Contracts/
      WorkingSchedules/
      Attendance/
      TimeOff/ (Requests, Allocations, Types)
      Payroll/ (Payruns, Payslips, SalaryStructures, SalaryRules)
      Admin/ (Users, Roles)
    components/               # dumb, reusable presentational components
    api/                      # typed API client functions, one file per module
    hooks/                    # data-fetching hooks wrapping api/
    auth/                     # role-based route guards, current-user context
    types/
```

## Boundary Rule (repeated for emphasis)

- API/route layer: auth + input validation + call one service function + shape response.
- Service layer: orchestration, calls business-rule modules, talks to DB via ORM.
- `payroll/` modules: pure(ish) business logic, unit-testable without HTTP or DB mocks where possible.
- Frontend components: render + call `api/` functions; no payroll math client-side beyond display formatting.
