# Payloom — Architecture for the Demo (Phase 12)

Two diagrams and a talk track. The **key visual point**: the AI provider sits *outside* the
financial calculation path.

---

## Diagram 1 — System architecture

```text
                    ┌─────────────────────────────────┐
                    │   React + TypeScript frontend    │
                    │   (Vite · Tailwind · Axios)      │
                    └───────────────┬─────────────────┘
                                    │  REST / JWT
                    ┌───────────────▼─────────────────┐
                    │        FastAPI backend           │
                    │   auth · RBAC · error envelope   │
                    └───────────────┬─────────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        │                    Domain services                    │
        │  HR · Attendance · Time Off                            │
        │  Payroll Engine  ── execute_rules() ── AST evaluator   │
        │  PayTrace   (reads PayslipLine snapshots)              │
        │  Preflight  (13 deterministic checks + validation gate)│
        │  Simulator  (reuses execute_rules(), transient rules)  │
        │  Intelligence — Evidence Builder + source registry     │
        └───────────────────────────┬───────────────────────────┘
                                    │
                    ┌───────────────▼─────────────────┐
                    │      SQLAlchemy + Alembic         │
                    └───────────────┬─────────────────┘
                                    │
                    ┌───────────────▼─────────────────┐
                    │        Neon PostgreSQL           │
                    └─────────────────────────────────┘

   ── AI path (optional, outside the money path) ──────────────────

   Evidence Builder ──► sanitized JSON ──► AI provider (Gemini)
        │                                        │
        │                              structured brief (JSON)
        ▼                                        ▼
   source registry ◄──── backend claim validation ────┘
        │            (unknown source / bad number / severity → dropped)
        ▼
   Grounded Payroll Brief  ──►  frontend
```

**Talk track (20 s):**
> "One backend, one payroll engine. PayTrace, Preflight and the Simulator all sit on top of that same deterministic engine. The AI provider is over here — it only ever receives sanitized, already-computed outputs, and everything it says is validated against a source registry before it's rendered. If it's gone, everything to the left of it still works."

---

## Diagram 2 — Payroll domain flow

```text
        Employee
           │
        Contract ───────── Working Schedule
     (period-aware,          (expected work)
      date-bound)
           │
     Attendance + Approved Time Off      ← operational context
           │                               (exposed to rules,
           ▼                                 not auto-applied)
     Salary Structure
           │
     Ordered Salary Rules   (FIXED · PERCENTAGE · FORMULA)
        seq 1  BASIC     50% of CONTRACT_WAGE
        seq 10 HRA       20% of BASIC
        seq 20 ALLOWANCE ₹2,000 fixed
        seq 60 GROSS     = BASIC + HRA + ALLOWANCE
        seq 80 PF        10% of BASIC
        seq 100 NET      = GROSS − PF
           │
           ▼
        Payrun  (DRAFT → COMPUTED → VALIDATED → PAID)
           │
           ▼
        Payslip + PayslipLine snapshots
           ├──► PayTrace        WHY?      (deterministic, from snapshots)
           ├──► Preflight       SAFE?     (13 checks + server-side gate)
           └──► PDF                       (ReportLab, from persisted data)

   Temporary rule overrides ──► same Payroll Engine ──► Simulator   WHAT IF?
                                                        (nothing persisted)

   Verified outputs ──► Payloom Intelligence            UNDERSTAND
                        (grounded, source-validated AI brief)
```

**Talk track (20 s):**
> "HR data on top creates the payroll *context*. The Salary Structure creates the *calculation*. Every Payslip line is snapshotted, so PayTrace can explain it forever and Preflight can verify it. The Simulator feeds temporary overrides through the *same* engine without persisting anything. And Payloom Intelligence turns those verified outputs into something a human can read."

---

## The one-sentence architecture answer

> "Payloom is a deterministic HR-and-payroll core — `Decimal` arithmetic, ordered Salary Rules, a snapshotting engine — with four layers on top: PayTrace explains the result, Preflight verifies it before money moves with a server-side gate, the Simulator tests rule changes through the same engine without touching real data, and Payloom Intelligence turns verified outputs into a grounded, source-linked AI brief. AI is never in the calculation path."

---

## If you need slides later (content only — don't build the PPT unless asked)

1. **Problem** — payroll depends on everything upstream; fragmented systems = reconciliation + blame
2. **Payloom** — HR & Payroll, woven together (the domain flow diagram)
3. **Architecture** — system diagram; emphasize the AI boundary
4. **Core payroll engine** — ordered rules, `Decimal`, snapshots, the canonical ₹29,500 example
5. **EXPLAIN → VERIFY → SIMULATE → UNDERSTAND** — PayTrace / Preflight / Simulator / Intelligence, one slide
6. **Tech + security + AI boundary** — stack, RBAC, data minimization, graceful degradation
7. **Impact + limitations + future** — honest scope, extension points

The live product is the centerpiece. Slides are backup.
