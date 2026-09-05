# Payloom — Claims Matrix (Phase 12)

Internal anti-bluffing table. Before saying something to a judge, check it's in the **YES** column.
"Safe to say" means: it is true of the code at feature freeze and can be shown or pointed to.

| Claim | Evidence | Safe to say? |
|---|---|---|
| "HR & Payroll, woven together" — one traceable workflow | Employee → Contract → Schedule → Attendance/Leave → Structure/Rules → Payrun → Payslip, all linked in one app + DB | **YES** |
| Payroll is deterministic — same inputs, same output | `Decimal` + `ROUND_HALF_UP`, sequence-ordered rule execution, no randomness, no AI in the path | **YES** |
| The canonical example produces exactly ₹29,500 | `test_payroll_engine` asserts BASIC 25k → HRA 5k → ALLOWANCE 2k → GROSS 32k → PF 2.5k → NET 29.5k; verified live on Neon | **YES** |
| Salary is not hardcoded — rules drive everything | Category totals are the sum of that Payslip's own lines; GROSS/NET are ordinary FORMULA rules | **YES** |
| The formula evaluator is safe (no `eval`/`exec`) | `formula_engine.py` walks an AST, whitelists arithmetic + `rules[...]`/`categories[...]` subscripts only | **YES** |
| Forward references between rules are impossible | `rules`/`categories` dicts only contain already-executed rules | **YES** |
| Historical payroll is traceable | PayslipLine snapshots + PayTrace rebuilt from them | **YES** |
| A finalized Payslip doesn't change when its rule is edited later | historical-integrity test; demo: Dave's Feb payslip still ₹35,000 on the old ₹60k contract | **YES** |
| PayTrace is not an AI reconstruction | it reads only persisted snapshots; no LLM call in `/trace` | **YES** |
| Preflight catches problems before money moves | 13 deterministic checks; demo shows `MISSING_APPLICABLE_CONTRACT` blocker | **YES** |
| The validation gate is server-side and can't be bypassed | `validate_payrun` recomputes + re-runs Preflight, `409 VALIDATION_BLOCKED` on any blocker | **YES** |
| Preflight uses no AI | zero LLM references in `preflight.py`; readiness is a pure function of counts | **YES** |
| The Simulator reuses the real engine, not a copy | both call `execute_rules()`; baseline-equivalence test (zero overrides == normal calc) | **YES** |
| The Simulator persists nothing | transient `SalaryRule` objects never `db.add()`'d; DB-non-mutation test (byte-identical before/after) | **YES** |
| After simulating HRA at 25%, the real rule is still 20% | shown live in the demo; non-mutation test | **YES** |
| The annualized number is an *estimate* | labelled "annualized estimate", only shown for 28–31 day periods, `monthly × 12` | **YES** |
| AI only explains — it never calculates payroll | Intelligence + narrator receive computed outputs; no rule execution in either | **YES** |
| Every significant AI statement cites a Payloom source | `_validate_items` drops items with no/unknown `source_ids`; source labels rendered in UI | **YES** |
| AI can't upgrade a WARNING to a BLOCKER | severity normalized to the cited source's deterministic value; test `test_severity_cannot_be_upgraded_by_ai` | **YES** |
| A hallucinated rupee figure is rejected before display | `_grounded_numbers` check; test `test_numeric_hallucination_is_dropped` | **YES** |
| The AI never sees names / bank / IDs / secrets | evidence packet uses `EMP-####` codes; privacy test asserts the JSON contains none of those | **YES** |
| If AI fails, everything else keeps working | `run()` never raises; deterministic fallback brief; Phase 11 verified with no key | **YES** |
| The API key is never exposed to the frontend | backend-only env var; frontend calls the Payloom backend; bundle grepped clean | **YES** |
| An employee can't read another employee's payslip | `_assert_payslip_access` ownership check; RBAC tests | **YES** |
| Overlapping contracts are treated as an integrity problem | blocked at creation; `CONTRACT_CONFLICT` blocker if they exist | **YES** |
| Payroll resolves the contract for the *period* | `get_applicable_contract`; demo: Aarav ₹70k(2025) vs ₹85k(2026) | **YES** |
| Backend re-validates employee eligibility (frontend not trusted) | `create_payrun` re-checks every id; Simulator re-checks; `eligible-employees` is a preview only | **YES** |
| 200 backend tests pass | `pytest` — 200 passed, Phase 11 report | **YES** |
| — | — | — |
| "AI calculates / predicts payroll" | false — architecturally excluded | **NO — never say** |
| "Attendance automatically reduces salary" | only if a Salary Rule formula uses `worked_days`/`approved_leave_days`; none of the seeded rules do | **CONDITIONAL** — say "context only, a rule can use it" |
| "Payloom is statutory-compliant payroll" | no tax engine; PF/PT are example rules | **NO** — say "configurable examples, not compliance" |
| "Production-ready / enterprise-grade security" | hackathon build; real controls but no pen-test/cert/audit log | **NO** — say "real controls, not certified" |
| "Scales to millions of employees" | not load-tested; architecture has no obvious cliff | **CONDITIONAL** — say "architecturally sound, not load-tested at that scale" |
| "Sends payslips by email" | not built — no provider | **NO** |
| "Prorates a mid-period contract change" | not built — full structure applied, Preflight raises INFO | **NO** |
| "Real-time" anything | nothing is streamed/pushed; it's request/response | **NO** — say "derived live on load" |
| "We rehearsed the spoken demo N times" | only true if a human actually did — the build agent can't rehearse delivery | **CONDITIONAL** — see `COMPLETION` note; mark human rehearsal required |
