# Payloom

<p align="center">
  <strong>HR & Payroll, woven together.</strong>
</p>

<p align="center">
  A modern integrated HR and payroll operations platform that connects employee records, contracts, schedules, attendance, time off, salary rules, payruns and payslips into one traceable workflow.
</p>

---

## Overview

**Payloom** is an integrated Human Resource and Payroll Operations Platform built for the Odoo Hackathon 2026.

Instead of treating HR and payroll as disconnected modules, Payloom connects the entire employee lifecycle:

```text
Employee
   ↓
Contract
   ↓
Working Schedule
   ↓
Attendance + Time Off
   ↓
Salary Structure + Salary Rules
   ↓
Payrun
   ↓
Payslip
   ↓
Validation
   ↓
Payment Status
```

The goal is simple:

> make payroll understandable, auditable and driven by real HR data instead of disconnected spreadsheets and opaque calculations.

---

## Why Payloom?

Payroll usually depends on information spread across multiple systems:

- employee master data
- contracts and wage history
- working schedules
- attendance
- leave balances
- payroll configuration
- salary formulas

Payloom brings those relationships into a single workflow so that every Payslip can be traced back to the employee's employment context and the Salary Rules that produced it.

The core mental model is:

```text
Salary Structure tells HOW to calculate
Payroll Period tells WHEN
Payrun tells WHO is processed together
Payslip tells WHAT one employee receives
Payslip Lines explain WHY
```

---

## Core Features

| Module | What Payloom Does |
| --- | --- |
| **Authentication & RBAC** | Login, protected modules, role-aware access and admin-managed user accounts |
| **Employee Management** | Kanban/List views, employee profile, Department, Manager, Job Position and Working Schedule relationships |
| **Contracts** | Historical employment contracts, wage, dates, salary structure and overlap validation |
| **Working Schedules** | Weekly work patterns with start/end time, break duration and derived weekly hours |
| **Attendance** | Global and employee-specific attendance, Check In / Check Out, live elapsed session, worked hours and HR corrections |
| **Time Off** | Leave types, allocations, approval/refusal flow and automatically derived leave balances |
| **Salary Structures** | Groups the ordered Salary Rules used during payroll computation |
| **Salary Rules** | FIXED, PERCENTAGE and safe FORMULA-based salary calculations |
| **Payruns** | Two-step employee-selection workflow and payroll lifecycle management |
| **Payslips** | Real payroll computation, line-by-line salary trace, warnings and historical snapshots |
| **Payslip PDF** | Generates a real PDF from persisted payroll data |
| **Payroll Preflight** | Surfaces blockers and warnings before payroll is validated |
| **Payroll Simulator** | Deterministic what-if scenarios — reruns the real Salary Rule engine against temporary overrides, never persists anything |
| **Payloom Intelligence** | Grounded AI payroll brief — turns verified Preflight/payroll facts into a source-linked summary; AI communicates, never calculates, and payroll works without it |

---

## Payroll Workflow

```mermaid
flowchart LR
    A[Employee] --> B[Applicable Contract]
    B --> C[Working Schedule]

    D[Attendance] --> H[Payroll Context]
    E[Approved Time Off] --> H
    C --> H
    B --> H

    F[Salary Structure] --> G[Ordered Salary Rules]
    G --> H

    H --> I[Salary Rule Engine]
    I --> J[Payslip Lines]
    J --> K[Payslip]
    K --> L[Payrun]

    L --> M[DRAFT]
    M --> N[COMPUTED]
    N --> O[VALIDATED]
    O --> P[PAID]
```

Payrun processing uses the explicit lifecycle:

```text
DRAFT → COMPUTED → VALIDATED → PAID
```

---

## Payrun Creation — Two-Step Flow

Payloom deliberately separates payroll scope selection from actual Payrun creation.

```mermaid
sequenceDiagram
    participant U as Payroll User
    participant UI as Payloom UI
    participant API as FastAPI Backend
    participant DB as PostgreSQL

    U->>UI: New Payrun
    UI->>U: Select Salary Structure + Period
    U->>UI: Continue
    UI->>API: Fetch eligible employees
    API-->>UI: Eligible / Ineligible employees
    Note over API,DB: No Payrun is created here

    U->>UI: Select employees
    U->>UI: Create Payrun
    UI->>API: POST selected employee IDs
    API->>API: Revalidate employee eligibility
    API->>DB: Create Payrun + selected Payslips
    DB-->>API: Created
    API-->>UI: DRAFT Payrun
```

---

## Salary Rule Engine

Salary Rules are not reference data — they actively drive payroll calculations.

Supported rule categories include:

```text
BASIC
ALLOWANCE
GROSS
DEDUCTION
NET
```

Supported computation methods include:

```text
FIXED
PERCENTAGE
FORMULA
```

### Example

```text
Contract Wage
     ↓
BASIC
     ↓
HRA
     ↓
Allowances
     ↓
GROSS
     ↓
Deductions
     ↓
NET
```

Each result is persisted as a **Payslip Line**, which lets the system explain how a Payslip was calculated even after payroll configuration changes later.

---

## PayTrace — Explainable Payroll

A Payslip should not only show a final Net Salary.

Payloom stores computation metadata such as:

```text
Rule Name
Rule Code
Category
Sequence
Computation Method
Base Description
Amount
```

This makes salary calculation traceable instead of opaque.

Example:

```text
House Rent Allowance
Code: HRA
Method: Percentage
Base: BASIC
Result: ₹10,000
```

---

## Payroll Preflight

> **PayTrace tells us *why* payroll produced a number. Preflight tells us *whether* we're comfortable letting that number move forward.**

Payroll Preflight is a **deterministic payroll readiness & risk engine**. After
a Payrun is computed, Preflight inspects it against the actual database and
reports whether it is safe to finalize — with evidence, not vibes. No AI is
involved anywhere in the engine.

```text
Create Payrun → Compute → PREFLIGHT → Fix issues → Validate → Mark Paid
```

It is a **derived assessment** — it persists nothing and adds no Payrun status.
Readiness is a pure function of the finding counts:

```text
NOT_RUN            (Payrun still in DRAFT)
ACTION_REQUIRED    any BLOCKER present
REVIEW_RECOMMENDED no blockers, some warnings
READY             no blockers, no warnings
```

13 registered checks across contract, payroll-configuration, payslip-integrity,
attendance, time-off, variance and duplicate dimensions, e.g.:

```text
BLOCKER   No applicable contract for 01–30 Sep 2026
BLOCKER   Two contracts overlap the payroll period
BLOCKER   Persisted Payslip totals disagree with the calculation lines
WARNING   Net Pay increased ₹11,700 (+39.66%) vs the previous Payslip — review recommended
WARNING   3 Attendance records have no check-out inside the period
INFO      2 approved leave days overlap this period (pay is not reduced)
```

Every finding carries a stable `code`, a severity (`BLOCKER` / `WARNING` /
`INFO` — the existing vocabulary), an `evidence` object, and a `resolution`.

**The validation gate is server-side and independent of the client.** `Validate`
recomputes every Payslip and then re-runs the whole Preflight engine on the
backend; if any blocker exists it aborts (`409 VALIDATION_BLOCKED`). A stale
"READY" in the browser — or a direct API call — cannot bypass it. If Payloom
says **READY TO VALIDATE**, the backend actually checked.

---

## Payroll Simulator — What-If Analysis

> **PayTrace explains WHY. Preflight checks IF IT'S SAFE. Simulator answers WHAT IF.**

"What happens if we change HRA from 20% to 25% before we actually change it?"
The Simulator answers this by rerunning **the exact same Salary Rule engine**
used for real payroll — never a second calculator — against temporary,
in-memory rule overrides for a chosen structure, period and employee set.

```text
Real Salary Rules + Temporary Overrides + Employees + Period
                        ↓
              Canonical Payroll Engine
                        ↓
              Ephemeral Simulation Result
                        ↓
                    Discarded
```

**Nothing is ever persisted.** Overridden rules exist only as transient
objects that are never added to the database session — there is no code
path that can write them, by construction, not by convention. No Payrun,
Payslip, or PayslipLine is created. A change to an upstream rule (e.g. HRA)
correctly recalculates every downstream value (GROSS, NET) through the real
formula dependency chain — never a hand-added delta — while unrelated rules
(BASIC, PF) are correctly left unchanged.

Available at `/payroll/simulator` for `HR_PAYROLL_MANAGER`/`ADMIN` only.
Shows per-employee and company-wide impact, a component-level breakdown per
rule, and — only when the selected period looks like one calendar month —
an annualized estimate (`monthly delta × 12`), clearly labeled as an
assumption, never a forecast.

---

## Payloom Intelligence — Grounded AI Payroll Briefing

> **EXPLAIN → VERIFY → SIMULATE → UNDERSTAND**
> PayTrace explains WHY. Preflight checks IF IT'S SAFE. Simulator answers
> WHAT IF. Intelligence answers WHAT SHOULD I UNDERSTAND.

Payloom Intelligence is a grounded AI layer that sits **above** the
deterministic engines. On a computed Payrun, **Generate Payroll Brief**
turns the verified facts into a short operational brief: scope, totals,
the Preflight items that need attention, and a suggested review order.

```text
Payroll Engine → PayTrace → Preflight → Simulator
        ↓ verified structured evidence + source registry ↓
              Payloom Intelligence (AI communicates)
        ↓ backend validates every claim against the registry ↓
                  Grounded Payroll Brief
```

**The AI never calculates payroll.** It receives a sanitised evidence
packet (employee *codes* only — never names, bank details, IDs, contact
info or secrets) in which every fact already has a stable id, a
Payloom-owned severity, and a pre-computed number. The model may only
cite ids from that registry. The backend then **validates every claim**:

- an item citing an unknown source, or no source, is dropped
- severity is normalised to the cited source's deterministic value — the
  AI cannot upgrade a warning to a blocker
- any ₹ figure not present verbatim in a cited source is rejected

**If the AI is unavailable** (no key, timeout, provider error, bad
output), the brief falls back to a deterministic summary generated by
Payloom code and clearly labelled as such. No payroll function ever
depends on AI availability.

Every statement in the brief shows its provenance — `Source: Preflight ·
MISSING_APPLICABLE_CONTRACT · EMP-0018` — linking straight to the
relevant view. A visible disclosure states that payroll calculations are
deterministic and are not performed by AI.

Available on the Payrun detail page for
`HR_PAYROLL_USER`/`HR_PAYROLL_MANAGER`/`ADMIN`. Configured via a single
pluggable provider — `AI_PROVIDER` (`gemini` by default, or `anthropic`)
plus that provider's API key (see `.env.example`); the same provider
powers the Payslip-level **Explain in Simple Language** on the PayTrace
view.

---

## Attendance Workflow

```mermaid
stateDiagram-v2
    [*] --> NotCheckedIn
    NotCheckedIn --> CheckedIn: Check In
    CheckedIn --> Completed: Check Out
    Completed --> [*]
```

Payloom Attendance supports:

- global Attendance view
- employee-filtered Attendance
- quick Check In / Check Out
- live elapsed time
- worked-hours calculation
- HR corrections
- overlap/session protection

Attendance is designed as the employee's **actual work record**, while Working Schedule represents the **expected work pattern**.

---

## Time Off Workflow

```mermaid
flowchart TD
    A[Time Off Type] --> B[Allocation]
    B --> C[Employee Request]
    C --> D{Approval}
    D -->|Approve| E[Approved Request]
    D -->|Refuse| F[Refused Request]
    E --> G[Balance Consumption]
```

The key balance rule is:

```text
Remaining Balance
=
Approved Allocation
-
Approved Consumed Leave
```

Pending and refused requests do not consume the final available balance.

---

## Role-Based Access Control

Payloom uses five application roles:

| Role | Access |
| --- | --- |
| `EMPLOYEE` | Own Attendance, own Time Off and own Payslips |
| `HR_MANAGER` | Employee, Contract, Schedule, Attendance and Time Off operations |
| `HR_PAYROLL_USER` | HR access + Payrun/Payslip operations, Salary Configuration read-only |
| `HR_PAYROLL_MANAGER` | Full payroll operations + Salary Structure/Rule management |
| `ADMIN` | Full platform access including User Management |

Authentication, protected API routes and role-aware operations are enforced on the backend, not only through hidden frontend controls.

---

## System Architecture

```mermaid
flowchart TD
    A[User] --> B[React + TypeScript Frontend]

    B --> C[REST API]

    C --> D[FastAPI Backend]

    D --> E[Authentication + RBAC]
    D --> F[HR Services]
    D --> G[Attendance Services]
    D --> H[Time Off Services]
    D --> I[Payroll Engine]

    F --> J[(PostgreSQL)]
    G --> J
    H --> J
    I --> J

    I --> K[Salary Rule Engine]
    K --> L[Payslip Lines]
    L --> M[Payslip PDF]

    J --> N[Operational Data]
    N --> B
```

---

## Tech Stack

### Frontend

- React 19
- TypeScript
- Vite
- React Router
- Tailwind CSS
- Axios
- Lucide React

### Backend

- FastAPI
- SQLAlchemy
- Pydantic
- Alembic
- PostgreSQL / Psycopg
- PyJWT
- Passlib + bcrypt
- ReportLab
- Pytest

---

## Repository Structure

```text
Odoo-Hackathon-2026/
│
├── frontend/
│   ├── src/
│   ├── public/
│   ├── package.json
│   └── vite.config.ts
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── main.py
│   ├── migrations/
│   ├── tests/
│   ├── alembic.ini
│   └── requirements.txt
│
├── docs/
│   ├── API_CONTRACT.md
│   ├── BUILD_STATUS.md
│   ├── DOMAIN_TERMS.md
│   ├── PHASE_LOG.md
│   └── ROUTES.md
│
├── docker-compose.yml
├── .env.example
└── readme.md
```

---

## Database Options

Payloom's backend is plain SQLAlchemy + Alembic + PostgreSQL — the
database can be either of these, switched purely via `DATABASE_URL` in
`.env`; no code differs between them:

1. **Local PostgreSQL via Docker** (default, see Quick Start below) —
   for day-to-day development.
2. **Neon** (managed cloud PostgreSQL) — for a persistent demo/deployment
   environment that doesn't depend on your machine being up. See
   [`docs/NEON_DEPLOYMENT.md`](docs/NEON_DEPLOYMENT.md) for the full setup,
   migration, and seeding steps.

Both use the same Alembic migration chain as the schema source of truth
— `alembic upgrade head` against whichever `DATABASE_URL` is active.

---

## Quick Start

### Prerequisites

Install:

```text
Node.js
npm
Python 3
Docker
```

### 1. Clone the repository

```bash
git clone https://github.com/Sreekuttan-007/Odoo-Hackathon-2026.git
cd Odoo-Hackathon-2026
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Current example:

```env
APP_ENV=development
SECRET_KEY=replace-this-with-a-long-random-secret
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
DATABASE_URL=postgresql+psycopg://peoplepay:peoplepay_dev_password@localhost:5433/peoplepay
```

### 3. Start PostgreSQL

```bash
docker compose up -d
```

### 4. Start the backend

```bash
cd backend
python -m venv venv
```

macOS / Linux:

```bash
source venv/bin/activate
```

Windows:

```bash
venv\Scripts\activate
```

Then:

```bash
pip install -r requirements.txt
alembic upgrade head
python seed.py   # idempotent demo data — safe to re-run
uvicorn app.main:app --reload
```

Backend:

```text
http://localhost:8000
```

Health check:

```text
GET http://localhost:8000/api/health
```

### 5. Start the frontend

Open another terminal:

```bash
cd frontend
npm install
npm run dev
```

Frontend:

```text
http://localhost:5173
```

---

## Testing

### Backend

```bash
cd backend
pytest
```

### Frontend

```bash
npm run build
npm run lint
```

---

## Project Screenshots

Add final screenshots to:

```text
docs/screenshots/
```

Recommended gallery:

```html
<table>
  <tr>
    <td><img src="./docs/screenshots/dashboard.png" width="600" alt="Payloom Dashboard"></td>
    <td><img src="./docs/screenshots/employees.png" width="600" alt="Employees"></td>
  </tr>
  <tr>
    <td><img src="./docs/screenshots/attendance.png" width="600" alt="Attendance"></td>
    <td><img src="./docs/screenshots/time-off.png" width="600" alt="Time Off"></td>
  </tr>
  <tr>
    <td><img src="./docs/screenshots/payrun.png" width="600" alt="Payrun"></td>
    <td><img src="./docs/screenshots/payslip.png" width="600" alt="Payslip"></td>
  </tr>
</table>
```

Do not add screenshot paths until those files actually exist.

---

## Demo Flow

A strong live demonstration is:

```text
1. Login as HR/Admin

2. Open an Employee
   → Department
   → Contract
   → Working Schedule

3. Open Attendance
   → Check In / Check Out
   → show worked-hours calculation

4. Open Time Off
   → show allocation
   → submit leave
   → approve it
   → show remaining balance update

5. Open Salary Structure
   → show ordered Salary Rules

6. Create a Payrun
   → choose structure + period
   → Continue
   → prove no Payrun exists yet
   → explicitly select employees
   → Create Payrun

7. Compute Payroll
   → open a Payslip
   → show rule-by-rule calculation
   → Basic / Allowances / Gross / Deductions / Net

8. Show payroll warnings / blockers

9. Validate

10. Mark Paid

11. Generate Payslip PDF
```

---

## What Makes Payloom Different?

Payloom is not just a collection of HR CRUD screens.

The platform is built around **traceability**:

```text
Employee
   ↓
Contract
   ↓
Schedule
   ↓
Attendance + Leave
   ↓
Salary Rules
   ↓
Payslip Calculation
```

That creates three important properties:

### 1. Explainable Payroll

Each salary amount can be traced to an ordered Salary Rule and persisted Payslip Line.

### 2. Safer Payroll Finalization

Preflight warnings and blockers are surfaced before validation.

### 3. Historical Integrity

Finalized payroll remains stable even if Salary Rules are edited for future periods.

---

## Known Scope Boundaries

Payloom should not be presented as a statutory payroll-compliance product.

The current project focuses on:

```text
HR operations
configurable salary computation
payroll workflow
traceability
validation
Payslip generation
```

It does **not** inherently claim:

```text
tax filing
government compliance filing
bank disbursement
PF/ESI statutory submission
multi-country payroll compliance
```

Any Salary Rules named after real-world deductions are configurable payroll examples unless compliance has been separately implemented and verified.

---

## Documentation

Technical documentation is available in:

- `docs/API_CONTRACT.md`
- `docs/DOMAIN_TERMS.md`
- `docs/ROUTES.md`
- `docs/BUILD_STATUS.md`
- `docs/PHASE_LOG.md`
- `docs/NEON_DEPLOYMENT.md`
- `docs/DEMO_HARDENING_REPORT.md`

---

## Repository

**GitHub:**  
https://github.com/Sreekuttan-007/Odoo-Hackathon-2026

---

<p align="center">
  <strong>Payloom</strong><br>
  HR & Payroll, woven together.
</p>
