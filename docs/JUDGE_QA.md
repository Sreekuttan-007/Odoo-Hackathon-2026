# Payloom — Judge Q&A Bank (Phase 12)

Every answer reflects the code that exists at feature freeze (Phase 11). Where behaviour is
deliberately *not* built, the answer says so. Don't bluff; honest boundaries build credibility.

---

## Problem & positioning

**1. What problem does Payloom solve?**
Payroll depends on data spread across HR systems — contracts, schedules, attendance, leave, salary configuration. When those are fragmented, payroll teams spend their time reconciling records and explaining why a number changed. Payloom weaves them into one traceable workflow, then adds a decision layer on top: explain the number, verify it before money moves, simulate changes safely, and turn verified results into a grounded brief.

**2. Is this an HR dashboard? An AI payroll app?**
Neither. The core is deterministic HR + payroll operations. AI is only the final explanation layer, and it is architecturally outside the calculation path.

**3. Why not just use an existing HRMS?**
The differentiator isn't another employee CRUD system — it's the layer around payroll: configurable deterministic Salary Rules, historical PayTrace, Preflight readiness with a server-side gate, a non-mutating Simulator, and a grounded AI brief. Most tools give you the number; Payloom gives you the number *and* its provenance, its safety check, and a safe way to test changes.

---

## Architecture

**4. Walk me through the architecture.**
React + TypeScript (Vite, Tailwind) frontend → FastAPI backend → domain services (HR, Attendance, Time Off, Payroll Engine, PayTrace, Preflight, Simulator, Intelligence evidence builder) → SQLAlchemy + Alembic → Neon PostgreSQL. The Intelligence evidence builder is the only thing that talks to the AI provider, and it sends sanitized, already-computed data.

**5. Where exactly is AI used?**
Two explanation surfaces, both optional: the **Payloom Intelligence** payroll brief (Payrun level) and **Explain in Simple Language** (Payslip / PayTrace level). Both receive sanitized structured outputs from the deterministic systems and only rephrase them. Payroll calculation, PayTrace evidence, Preflight severity and Simulator results never call the LLM.

**6. What's the tech stack — exactly?**
Frontend: React, TypeScript, Vite, Tailwind CSS, React Router, Axios. Backend: FastAPI, Python, SQLAlchemy, Pydantic, Alembic, PyJWT, passlib/bcrypt, ReportLab (PDF). DB: PostgreSQL on Neon. Tests: pytest (200 backend tests). AI: one provider, currently Google Gemini (`gemini-3.6-flash`), pluggable to Anthropic via one env var. There is no frontend unit-test suite — frontend checks are `tsc`, `vite build`, and `oxlint`.

---

## Payroll math & Salary Rules

**7. How is a Payslip actually calculated?**
A Salary Structure is an ordered list of Salary Rules. The engine resolves the applicable contract for the period, builds a context (contract wage, worked days, expected work days, worked/overtime hours, approved leave days), then executes the active rules in `sequence` order. Each rule's amount is quantized to 2 decimal places with `ROUND_HALF_UP` at the point it's produced. Category totals (BASIC/ALLOWANCE/GROSS/DEDUCTION/NET) are the sums of that Payslip's own line amounts — the engine never invents a total.

**8. FIXED vs PERCENTAGE vs FORMULA?**
FIXED: a fixed amount × quantity. PERCENTAGE: a percentage of `CONTRACT_WAGE` or of an earlier rule's result. FORMULA: a constrained expression that can reference `rules["CODE"]` and `categories["CATEGORY"]` for rules that have already executed.

**9. Is the formula evaluator safe? Do you use `eval`?**
No `eval`, no `exec`. `formula_engine.py` parses the expression to an AST and walks it, allowing only arithmetic operators and subscript access into `rules[...]` / `categories[...]`. Attribute access, function calls, names, imports and comprehensions are all rejected. A bad formula becomes a `RULE_FAILURE` warning on that Payslip — never a silent zero.

**10. What about forward references — rule B depending on rule C that runs later?**
Structurally impossible. `rules` and `categories` only ever contain rules that have *already* executed in sequence order, so a forward reference just isn't in the dict and the rule fails visibly.

**11. Floating point?**
Never for money. `Decimal` end-to-end, `ROUND_HALF_UP`, quantized to 2 places at each rule. The canonical worked example — ₹50,000 wage → BASIC ₹25,000 → HRA ₹5,000 → allowance ₹2,000 → GROSS ₹32,000 → PF ₹2,500 → NET ₹29,500 — is produced by the real engine, and there's a test asserting exactly that.

---

## Contracts

**12. What if an employee's salary changes mid-year?**
Contracts are historical and date-bound. Payroll resolves the contract applicable to the Payrun *period* rather than overwriting a salary field on the employee. Aarav in the demo has a ₹70,000 contract for Jul–Dec 2025 and an ₹85,000 one from Jan 2026 — a January Payrun uses ₹85,000.

**13. Mid-period contract changes / proration?**
Not implemented. The engine does not prorate a partial month. If a contract starts or ends inside the period, Preflight raises an INFO finding (`CONTRACT_STARTS_MID_PERIOD` / `CONTRACT_ENDS_MID_PERIOD`) noting the full structure was applied. That's a stated limitation and a natural extension point.

**14. Two contracts overlap a payroll period — which one wins?**
Neither silently. Overlapping contracts are blocked at contract creation (`assert_no_overlap`). If they somehow exist, `get_applicable_contract` raises `ConflictingContractsError`, eligibility fails, and Preflight raises a `CONTRACT_CONFLICT` **blocker**. Ambiguity is treated as an integrity problem, not a coin flip.

**15. Employee with no contract?**
Can't be added to a Payrun — eligibility check at creation returns `MISSING_CONTRACT` and the whole request is rejected (`INELIGIBLE_EMPLOYEES`). Eve in the demo is deliberately contract-less to show this.

---

## Attendance & Time Off

**16. Does attendance automatically change salary?**
Not in this version. Attendance is integrated operational *context* — the engine exposes `worked_days`, `expected_work_days`, `worked_hours`, `overtime_hours` to Salary Rules, and Preflight flags anomalies (missing check-outs, sessions > 16h, working far above schedule). But we deliberately don't claim a payroll deduction unless a Salary Rule's formula explicitly uses that data. That's honest scope, and it's future extensibility.

**17. How does Time Off integrate?**
Leave types → allocations → requests with an approve/refuse state machine. Balances are *derived* (`allocated − sum of approved consumed`), never persisted, so double-approval can't double-deduct — there's a dedicated test for the canonical case (20 allocated / 5 pre-approved / 15 remaining → approve 3 → 12 remaining). `approved_leave_days` is exposed to the payroll context; Preflight raises an INFO when approved leave overlaps a period, explicitly noting pay is not reduced unless a rule uses it.

**18. What are the attendance safeguards?**
One open session per employee at a time, one record per day, overlap protection, HR-only corrections. Company-timezone normalization is handled explicitly because SQLite drops tzinfo on round-trip (tests use SQLite; production is Postgres).

---

## PayTrace

**19. What if a Salary Rule changes next month — does PayTrace change?**
No. When a Payslip is computed, every line snapshots its rule name, code, category, sequence, computation method, the resolved percentage/base amount/fixed amount, and formula inputs. PayTrace is rebuilt entirely from those snapshots — it never reads the current (possibly edited) SalaryRule or Contract. A September payslip computed at HRA 20% still shows 20% after HRA is changed to 25%. There's a historical-integrity test for exactly this.

**20. Is PayTrace an AI feature?**
No. PayTrace is fully deterministic. The optional "Explain in Simple Language" button calls the LLM to rephrase the verified trace in plain language — and even there, any rule code the model returns is filtered against the trace's real rule codes, so a hallucinated component can't pass through.

**21. Legacy payslips without the new snapshot fields?**
PayTrace falls back to the human-readable `base_description_snapshot` string for those lines rather than fabricating structured numbers it doesn't have.

---

## Preflight

**22. How is Preflight different from validation?**
Preflight is the *explainable readiness* layer — it surfaces blockers, warnings and INFO findings with evidence and a resolution, and persists nothing. Validation is the *authoritative* state transition: it recomputes every Payslip and re-runs the entire Preflight engine server-side, and aborts with `409 VALIDATION_BLOCKED` on any blocker. The UI cannot bypass a blocker with a stale "READY".

**23. How many checks, and across what?**
13 registered checks across contract applicability, contract conflict, duplicate payslip, salary-structure availability, computation integrity (bridging the engine's own `RULE_FAILURE` warnings), payslip-total integrity (Decimal-exact, never a float compare), negative/impossible net, extreme deductions, attendance completeness, attendance anomalies, time-off context, salary variance vs the previous payslip, and contract/period boundary.

**24. Does Preflight use AI?**
No. Zero AI anywhere in the engine. Readiness is a pure function of the finding counts: any blocker → ACTION_REQUIRED; else any warning → REVIEW_RECOMMENDED; else READY.

**25. A check itself throws — what happens?**
It fails *safe*: the exception is logged and converted into a `PREFLIGHT_CHECK_ERROR` blocker, so Preflight never silently declares payroll READY when a check couldn't complete.

---

## Simulator

**26. Does simulation change the real Salary Rules?**
No. Overridden rules are represented as transient `SalaryRule` objects that are never handed to the DB session — there's no code path that can write them, by construction. No temporary Payrun, Payslip or PayslipLine is created. In the demo we run HRA 20%→25% and then show the real rule is still 20%.

**27. How do you know the simulation is right?**
It calls the exact same `execute_rules()` function that produces real Payslips — not a second calculator. A zero-override simulation is required to equal the normal calculation, and there's a baseline-equivalence test for that. An upstream change (HRA) recalculates every downstream value (GROSS, NET) through the real dependency chain; unrelated rules (BASIC, PF) are untouched.

**28. Company-wide impact / annualization?**
The Simulator aggregates per-employee deltas into a company total, and — only when the period spans 28–31 days — shows `monthly delta × 12` as an **annualized estimate**, explicitly labelled an estimate, not a forecast. No headcount growth, inflation or attrition modelling.

**29. Employee that can't be simulated?**
Returned as excluded with a real reason (`exclusion_code` / `exclusion_reason`) — e.g. no applicable contract, or an overlapping Payslip already exists for that period. Never a fabricated number.

**30. Does the Simulator persist anything for the demo?**
No. The Phase-9 DB-non-mutation test snapshots SalaryRule / Structure / Contract / Payslip / Warning / Attendance / TimeOff state before and after a multi-override run and asserts byte-identical.

---

## AI / Payloom Intelligence

**31. Why not use AI to calculate payroll?**
Payroll is financial infrastructure — it has to be deterministic and reproducible. Salary Rules and `Decimal` arithmetic calculate payroll. AI is used where it's strong — communicating and summarizing verified information — not where a hallucination could move money.

**32. How do you prevent hallucinations?**
The model never gets an open database or an open-ended prompt. The backend builds a sanitized evidence packet where every fact has a stable source ID, a backend-owned severity, and a pre-computed number. The model returns structured JSON that must cite those IDs. The backend then validates: an item citing an unknown ID or no ID is dropped; a claimed severity is overridden by the cited source's real severity (AI can't upgrade a WARNING to a BLOCKER); a rupee figure that doesn't appear verbatim in a cited source is rejected. There are tests for each of these.

**33. What data does the AI see? Privacy?**
Employee *codes* (`EMP-0004`), never names. Never bank details, government IDs, addresses, phone, email, tokens or secrets. There's a test that dumps the evidence packet's JSON and asserts none of those appear. Data minimization is by design — the packet contains only what's needed to describe the brief.

**34. Where does the API key live?**
Backend only, from an environment variable. The frontend never sees it and never calls the provider directly — it calls the Payloom backend, which calls the provider.

**35. AI provider goes down mid-demo — then what?**
Payroll, PayTrace, Preflight, the Simulator, validation and PDF all keep working. The brief endpoint returns `available: false` with a reason **and** a deterministic summary generated by backend code (clearly labelled "not AI-generated"). No payroll function depends on AI availability. `run()` never raises.

**36. Is the AI brief cached or persisted?**
No. It's generated on demand and persists nothing. The response carries an `evidence_fingerprint` so a client could detect stale data, but we deliberately didn't add persistence just for AI.

**37. Which provider, and why?**
Google Gemini (`gemini-3.6-flash`) via `AI_PROVIDER=gemini`. It's fast, has a native JSON response mode, and the free tier is enough for a demo. The provider is pluggable — `AI_PROVIDER=anthropic` switches to Claude with one env var, no code change. One provider at a time.

---

## Security

**38. How is auth handled?**
JWT bearer tokens (HS256), passwords hashed with bcrypt via passlib. Every non-public route depends on `get_current_user`; role-specific routes add `get_current_payroll_operator` / `get_current_payroll_manager` / `get_current_hr` / `get_current_admin`.

**39. RBAC — who can do what?**
EMPLOYEE: own attendance, own time off, own finalized payslips. HR_MANAGER: employee/contract/schedule/attendance/time-off operations — **no payroll**. HR_PAYROLL_USER: HR + Payrun/Payslip operations, read-only salary config. HR_PAYROLL_MANAGER: full payroll + Salary Structure/Rule config + Simulator. ADMIN: everything including user management. Enforced on the backend — hidden frontend controls are not the security boundary.

**40. Can an employee read someone else's payslip / trace / PDF?**
No — `_assert_payslip_access` checks `payslip.employee_id == current_user.employee_id` for non-HR roles, and only returns finalized payslips to the owning employee. The Payrun-level AI brief is payroll-operator-only; EMPLOYEE and HR_MANAGER get `403`.

**41. Secrets in the frontend bundle?**
Verified none — the built `dist/assets/*.js` was grepped for API keys and DB credentials in the Phase 11 hardening pass.

**42. Is this enterprise-grade / certified security?**
No — it's a hackathon build. The controls above are real (backend RBAC, hashing, protected APIs, env secrets, ownership checks, AI data minimization), but there's no pen-test, no compliance certification, no audit logging beyond application logs.

---

## Database, Neon, scale

**43. Why Neon?**
Managed serverless PostgreSQL — the same SQLAlchemy + Alembic stack works against local Docker Postgres or Neon with zero code change, just `DATABASE_URL`. Neon gives a persistent demo environment that doesn't depend on a laptop being up. First query after idle takes ~6 s (cold compute); after that it's fast.

**44. Will this scale?**
Architecturally: PostgreSQL, stateless backend services, server-side *batch* payroll computation (one request computes the whole Payrun, not one HTTP call per employee), targeted queries, one shared payroll engine. Preflight and the Simulator build their context once per run rather than issuing per-employee queries. We haven't load-tested to thousands of employees — that's an honest hackathon boundary — but there's no architectural cliff.

**45. Migrations?**
Alembic, single head (`ea2fc0bd7980`), `current == heads`, no divergence. Schema source of truth is the migration chain.

---

## Historical integrity, PDF, failures

**46. Prove a finalized payslip is stable.**
Snapshots. Computed line amounts and calculation metadata are frozen onto PayslipLine at compute time; recompute is blocked once VALIDATED/PAID. There's a test that computes a payslip, edits its Salary Rule, and asserts the PAID payslip's numbers don't move. In the demo, Dave's February payslip still shows ₹35,000 (his old ₹60,000-wage contract) even though his contract is now ₹50,000.

**47. How is the PDF generated?**
ReportLab, from the persisted, already-computed Payslip data — it never recomputes. It's a render of the historical result.

**48. What if the PDF generation fails?**
Show the Payslip detail page — the same persisted line-by-line data the PDF renders. State it as a limitation honestly; don't fake it.

**49. What breaks if the backend or Neon is unreachable?**
Everything — it's a live system, there's no offline mode. The demo fallback for that is backup screenshots / a recording, clearly described as backup material, not live output.

---

## Novelty, limitations, future, team

**50. What's actually novel here?**
Not that we built another employee CRUD system. It's the decision layer around payroll: deterministic financial logic preserved, then explainability (PayTrace), readiness verification with a server-side gate (Preflight), safe non-mutating what-if analysis (Simulator), and grounded, source-validated AI communication (Intelligence) on top of verified outputs. `EXPLAIN → VERIFY → SIMULATE → UNDERSTAND`.

**51. What are the limitations?** (say these plainly)
No statutory tax engine. No bank/payment-rail integration. No automated payslip email (depends on deployment config, not built). Attendance and time-off are payroll *context*, not automatic salary adjustments. No mid-period proration. The Simulator evaluates scenarios; it never applies them. AI is explanatory, not authoritative. No workforce forecasting. No legal/compliance guarantee. 6 seeded employees (thinner than a "representative" headcount). No `HR_PAYROLL_USER` seed account. No frontend automated test suite.

**52. Future scope?**
Statutory payroll packs by jurisdiction, bank/payment integration, accounting/ERP export, multi-level approval chains, payroll reconciliation, rule templates, attendance-linked salary rules, audit exports, multi-company support. Not a dozen more AI gimmicks.

**53. What did the team actually build, and can you modify it?**
Frontend (React/TS app, ~30 pages/components), backend (FastAPI, ~11 routers, ~11 domain services), the schema + Alembic migrations, the deterministic payroll engine and its AST formula evaluator, the full Payrun state machine, PayTrace / Preflight / Simulator / Intelligence, 200 backend tests, and the Neon deployment. AI coding tools assisted development; the team can explain and change any part of it — ask us to walk through `payroll_engine.py` or `preflight.py` live.

**54. If you had one more week?**
Attendance-linked salary rules (unpaid-leave deduction driven by a rule formula, not hardcoded) and a statutory PF/PT template pack — both extend the existing rule engine rather than adding a parallel system.

**55. Anything you're *not* claiming?**
That AI calculates payroll (it doesn't). That attendance changes salary automatically (it doesn't, yet). That this is statutory-compliant payroll (it isn't — the PF/PT rules in the demo are configurable examples). That it's been tested at enterprise scale (it hasn't).
