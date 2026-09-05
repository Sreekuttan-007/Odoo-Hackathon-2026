# Payloom — Final Demo Script (Phase 12)

**Target duration:** ~5:00 (hard cap 5:30). **Presenter:** 1 driver + 1 narrator, or 1 person doing both.
**Login for the whole demo:** `admin@payloom.local` / `admin123` (ADMIN — reaches every screen; no logout mid-demo).
**Product story:** *HR & Payroll, woven together.* **Innovation story:** *EXPLAIN → VERIFY → SIMULATE → UNDERSTAND.*

> Every line below is speakable as-is. Bold = say it. Plain = stage direction. Each segment has a **Fallback** if the click fails.

---

## Pre-staged records (see `DEMO_CHECKLIST.md` to arm)

| Record | Purpose | State needed |
|---|---|---|
| **Dave Staff** (`EMP0004`, `employee@payloom.local`) | canonical demo employee, wage ₹50,000 | contract `end_date` = **null** (disarmed) at demo start |
| **PR/2026/0005** — Dave, Dec 2026 | the Compute demo | **DRAFT** |
| **PR/2026/0004** — Dave, Oct 2026 | the Preflight-blocker demo ("Payrun A") | **COMPUTED**; armed just before the demo |
| **PR/2026/0003** — Dave, Sep 2026 (₹29,500) | PayTrace + Intelligence | **COMPUTED** |
| **PR/2026/0001** — Feb 2026 | Paid payslip + PDF ("Payrun B" for the paid path uses **0005**) | **PAID** |
| **Aarav Mehta** (`EMP0006`) | period-aware contract story (₹70k Jul–Dec 2025, ₹85k Jan 2026→) | 2 non-overlapping contracts |
| **Eve Unlinked** (`EMP0005`) | "missing contract = integrity problem" story | no contract |

---

## 0:00 – 0:30 · Problem + Payloom

Start on **`/dashboard`**, logged in.

> **"Payroll looks like a salary calculation. But the number depends on everything that happened before it — the employee's contract, their working schedule, attendance, leave, the salary structure and how its rules are configured."**

> **"When those systems are fragmented, payroll teams spend their time reconciling records, tracing errors, and explaining why a number changed. Payloom weaves them into one traceable workflow. HR and payroll, woven together."**

**Fallback:** if the dashboard is slow, talk over the loading state — the words matter more than the pixels.

---

## 0:30 – 0:55 · Dashboard

Gesture across the KPI row and attention items.

> **"This isn't a static analytics page. Every number here — active employees, running contracts, who's checked in, pending time-off — is derived live from the same operational records HR and payroll actually use."**

Don't open any chart. Move on.

**Fallback:** a failed section renders as a labelled empty card, not a crash — point to that as graceful degradation and continue.

---

## 0:55 – 1:20 · Employee → Contract

Click **Employees** → open **Dave Staff**.

> **"The employee is the hub — department, job position, manager, working schedule. But payroll never reads salary from a field on the employee."**

Open Dave's **contract** (from the employee page or `/contracts?employee_id=4`).

> **"Compensation lives on the contract, and contracts are historical and date-bound. Dave's is ₹50,000 a month from January 2026."**

Quickly open **Aarav Mehta** → contracts.

> **"Aarav has two contracts — ₹70,000 last year, ₹85,000 from January. Payroll resolves the contract that applies to the payroll *period*, it doesn't overwrite one salary field. And if two contracts ever overlapped a period, Payloom treats that as an integrity problem, not a coin flip."**

**Fallback:** if a detail page errors, go straight to `/contracts` and point at the two Aarav rows in the list.

---

## 1:20 – 1:40 · Attendance / Time Off

Open **`/attendance?employee_id=4`**, then **`/time-off/requests?employee_id=4`**.

> **"Expected work comes from the schedule. Actual work comes from attendance. Approved leave flows through allocations and requests, and balances are derived, never hand-edited."**

> **"In this version attendance and leave are integrated payroll *context* — the engine exposes worked days and approved leave days to Salary Rules, but we deliberately don't claim an automatic deduction unless a rule explicitly uses that data."**

**Fallback:** skip straight to Salary Structure; this segment is context-setting only.

---

## 1:40 – 2:05 · Salary Structure + Rules

Open **`/payroll/salary-structures`** → **Regular Salary**.

> **"This is where payroll stops being a black box. A Salary Structure is an *ordered* list of rules."**

Point down the list:

> **"BASIC is 50% of the contract wage. HRA is 20% of BASIC. A fixed allowance. GROSS is a formula over the earlier rules. PF is 10% of BASIC. NET is GROSS minus PF."**

> **"Rules run strictly in sequence, and a later rule can only reference results that already exist — so a forward reference is structurally impossible, not just discouraged. FIXED, PERCENTAGE and safe FORMULA are all supported, and formulas run through a constrained evaluator — no `eval`, no attribute access."**

**Fallback:** the structure list page shows the rule count; open any rule to show the FIXED/PERCENTAGE/FORMULA field.

---

## 2:05 – 2:30 · Payrun wizard + Compute

Click **Payruns → New Payrun**. Step 1: pick **Regular Salary** + any month. Click **Continue**.

> **"Continue shows me who's eligible — the backend re-checks every employee. Notice: no Payrun exists yet."**

Cancel out. Open the pre-made **PR/2026/0005 (Dave, December)** — it's **DRAFT**.

> **"Here's a DRAFT Payrun. Only explicit employee selection persists one."**

Click **Compute**.

> **"Compute runs the deterministic rule engine and *snapshots* every Payslip line — so this result stays stable even if the rules change later."**

Status flips **DRAFT → COMPUTED**.

**Fallback:** if the wizard misbehaves, go straight to PR/2026/0005 and Compute — the wizard point ("nothing persists on Continue") can be said without clicking it.

---

## 2:30 – 2:55 · PayTrace

Open Dave's Payslip in PR/2026/0005 (or use **PR/2026/0003**, also Dave, ₹29,500). Click **Explain salary** → PayTrace.

> **"Net is ₹29,500. Here's why, rule by rule: Contract Wage → BASIC ₹25,000 → HRA ₹5,000 → allowance ₹2,000 → GROSS ₹32,000 → PF ₹2,500 → NET ₹29,500."**

> **"This is not an AI reconstruction. PayTrace is rebuilt from the execution evidence stored when the Payslip was computed — the percentages, the base amounts, the formula inputs. If HRA changes to 25% next month, *this* payslip still shows 20%."**

Optionally click **Explain in Simple Language** (Gemini narrator).

**Fallback:** if the narrator button spins, cancel it — the deterministic trace above it is the point and stands alone.

---

## 2:55 – 3:25 · Preflight

Back to the Payrun list → open **PR/2026/0004 (Dave, October — the armed one)**.

> **"Calculating a number doesn't mean payroll is ready to move. Preflight inspects the computed Payrun against the live database."**

Preflight shows **ACTION REQUIRED · 1 blocker · MISSING_APPLICABLE_CONTRACT**.

> **"Someone changed Dave's contract dates after payroll was computed — now October has no applicable contract. Preflight caught it, with evidence and a resolution."**

Click **Validate**.

> **"And the gate is server-side."** — it's rejected (`409`).

> **"A stale 'ready' in the browser can't push a blocker through. Validation re-runs the whole Preflight engine on the backend before it commits."**

**Fallback (blocker not armed):** open **PR/2026/0003** instead — it's **READY**. Say: *"Here it's clean — no blockers, and the Validate button is live. Payloom also blocks bad Payruns at creation time, and the full blocker→fix→revalidate path is covered by our test suite."* Then continue.

---

### Transition
> **"PayTrace tells us *why* payroll produced a number. Preflight tells us *whether* we're comfortable letting that number move forward."**

---

## 3:25 – 3:55 · Simulator

Open **`/payroll/simulator`**. Scope: **Regular Salary**, **November 2026**, employee **Dave Staff**. Scenario: change **HRA from 20% to 25% of BASIC**. Run.

> **"Current net ₹29,500. Simulated ₹30,750. Plus ₹1,250 a month — and because this looks like a monthly period, an annualized estimate of ₹15,000, clearly labelled an estimate."**

Expand Dave's component comparison.

> **"BASIC, the allowance and PF are unchanged. HRA, GROSS and NET moved — recalculated through the *real* dependency chain, not a delta added to Net."**

> **"The simulator doesn't estimate payroll with AI. It reruns the same deterministic engine against a temporary scenario. Nothing is persisted —"** navigate to `/payroll/salary-rules`, show **HRA is still 20%**. **"— the real rule never moved."**

**Fallback:** if a period collides (`DUPLICATE_PAYSLIP` exclusion), switch the period to a later month with no Payslip for Dave; the numbers are identical.

---

### Transition
> **"PayTrace answers WHY. Preflight asks IS IT SAFE. Simulator answers WHAT IF."**

---

## 3:55 – 4:25 · Payloom Intelligence

Open **PR/2026/0004** (or 0003) → scroll to **Payloom Intelligence** → **Generate Payroll Brief**.

Brief renders: summary, Needs Attention, Observations, Suggested Review Order, Sources.

> **"This is an AI brief — but we deliberately do not let AI calculate payroll."**

> **"The backend builds a sanitized evidence packet: employee *codes*, not names; every fact carries a stable source ID and a number that Payloom already computed. The model can only cite those IDs. The backend then validates every claim — an unknown source, or a rupee figure that isn't in the evidence, is dropped before you ever see it."**

Expand a source: `Source: Preflight · MISSING_APPLICABLE_CONTRACT · EMP-0004`.

> **"Every significant statement points back to a Payloom source you can open."**

> **"The numbers come from Payloom. AI helps humans understand them."**

**Fallback (AI provider down):** the brief returns an *unavailable* banner **and** a deterministic summary generated by backend code. Say: *"If the provider is unavailable, payroll, PayTrace, Preflight, the Simulator, validation and PDF all keep working — only this optional brief degrades, and even then it falls back to a deterministic summary."* That's a strong architecture answer, not a failure.

---

## 4:25 – 4:45 · Validate → Paid → PDF

Back to **PR/2026/0005** (Dave, December — computed, clean).

Click **Validate** → **VALIDATED**. Click **Mark Paid** → **PAID**.

Open Dave's payslip → **PDF**.

> **"COMPUTED → VALIDATED → PAID. The PDF is generated from the same persisted result — it preserves the historical calculation, it doesn't recompute."**

**Fallback (PDF fails):** open the paid Payslip detail page and show the persisted line-by-line breakdown. Say: *"The PDF is a render of this persisted data — here's the data."* State it plainly, don't apologize.

---

## 4:45 – 5:00 · Close

> **"Payloom connects the HR records that create payroll context with the deterministic rules that calculate payroll."**

> **"And instead of stopping at a number, Payloom explains it, verifies it before money moves, simulates changes before they're committed, and turns those verified results into grounded intelligence."**

> **"Payloom — HR & Payroll, woven together."**

Stop. Don't keep talking.

---

## Time-compression options (if running long)

| Cut | Saves | Cost |
|---|---|---|
| Skip the wizard walkthrough, go straight to PR/2026/0005 Compute | ~20s | small — say the "nothing persists" line anyway |
| Skip "Explain in Simple Language" | ~15s | none — deterministic PayTrace is the point |
| Preflight fallback path (use PR/2026/0003 READY, don't arm the blocker) | ~15s | medium — lose the live "blocker caught" moment |
| One Intelligence source expansion instead of narrating the whole validation story | ~15s | small |

**Never cut:** PayTrace (the "not an AI reconstruction" line), Simulator non-mutation proof (HRA still 20%), Intelligence source provenance.

---

## 30-second elevator pitch

> "Payloom is an integrated HR and payroll operations platform. Employee contracts, schedules, attendance and leave provide the payroll context, while configurable Salary Rules deterministically generate every Payslip. What makes Payloom different is the layer around that calculation: PayTrace explains every salary component from stored execution evidence, Preflight catches issues before finalization with a server-side gate, the Simulator tests rule changes through the same engine without touching real payroll, and Payloom Intelligence turns those verified outputs into a grounded AI brief where every statement links back to a Payloom source."

## 60-second technical pitch

> "The domain model is Employee → date-bound Contract → Working Schedule → Attendance and Time Off → Salary Structure → ordered Salary Rules → Payrun → Payslip. The engine executes rules strictly in sequence — a later rule can only reference results that already exist — using `Decimal` arithmetic quantized with `ROUND_HALF_UP`, and formulas run through an AST evaluator with no `eval`, no attribute access, no calls.
>
> When a Payrun is computed, every Payslip line snapshots its rule metadata and resolved values, so PayTrace explains the historical calculation even after the rules change. Preflight is 13 deterministic checks producing blocker / warning / info findings with evidence; validation recomputes and re-runs the whole Preflight engine server-side, so a stale 'READY' in the browser can't push a blocker through.
>
> The Simulator reuses the exact same `execute_rules()` function against transient rule objects that are never added to the session — a zero-override simulation is required to equal the normal calculation, and there's a test asserting the database is byte-identical before and after.
>
> Payloom Intelligence builds a sanitized evidence packet — employee codes, not names — with a source registry, asks the LLM to communicate it as structured JSON, then validates every claim: unknown source, ungrounded number, or tampered severity, and the item is dropped. If the provider is down, it falls back to a deterministic summary and nothing else is affected."
