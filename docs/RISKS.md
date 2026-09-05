# RISK REGISTER — PeoplePay360

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Wrong period-based contract selection (falls back to "current contract" pointer) | Medium | High — every downstream payslip number is wrong | `getApplicableContract` is a single, unit-tested, pure function (CONTRACT_RULES.md); no other code path is allowed to read a contract for payroll purposes |
| Concurrent/conflicting ACTIVE contracts silently picked | Medium | High — masks a data-entry error as a valid payslip | Explicit conflict branch returns a blocking ERROR, never a "pick the first one" fallback |
| Salary Rule dependency bugs (rule referencing a later-sequenced rule) | Medium | High — wrong or crashing computation | Configuration-time validation rejects forward references before any Payrun ever runs (SALARY_RULE_ENGINE.md) |
| Unsafe formula evaluation (arbitrary code execution via FORMULA rules) | Low (if built correctly) | Critical — RCE via a config field | Whitelisted expression grammar only; no `eval`, no scripting sandbox; identifiers restricted to known rule codes |
| Duplicate Payslips | Medium | High — double pay reporting, wrong dashboard totals | DB-level unique constraint `(employee_id, payrun_id)`, not just a frontend check |
| Repeated Payrun Compute creates duplicates | Medium | Medium | Compute is an upsert keyed on the same unique constraint; re-running updates in place |
| Leave double-deduction | Low (by design) | Medium | Balance is derived via SUM over APPROVED rows, not imperatively decremented; approve action guarded by a status check |
| Inconsistent payroll state (e.g. Payslip PAID while Payrun DRAFT) | Low | High | Single state machine owns legal transitions; forbidden jumps explicitly rejected (PAYRUN_STATE_MACHINE.md) |
| Stale Dashboard metrics (hardcoded or cached-and-forgotten) | Medium | Medium — undermines the "connected system" pitch, easy to spot in a demo | Dashboard endpoints always query live rows at request time; no precomputed snapshot table for MVP |
| Editing finalized (PAID) payroll data | Low | High — destroys audit trust | PAID/VALIDATED Payslips are not exposed via any update endpoint; correction requires a documented-but-deferred reversal workflow |
| Email delivery failure | Medium | Low if isolated, High if coupled | `emailService` is called only from a dedicated `sendPayslips` action, decoupled from Compute/Validate/Mark Paid; failures produce a delivery warning, not a payroll rollback |
| PDF generation failure | Low | Low | PDF rendering is a pure function of already-persisted Payslip data; a failure blocks only the PDF request, not the Payrun state |
| Insufficient/incorrect permission enforcement | Medium | High — a demo where an Employee role can hit a payroll-admin action is a credibility failure | All authorization checks live server-side in the service layer, re-verified per request, independent of what the frontend renders |
| Feature creep beyond MVP scope | High (natural hackathon pull) | Medium — risks an incomplete P0 in favor of a partial P2 | MVP_SCOPE.md's Do-Not-Build list and phase gating in CLAUDE.md; P0 must be demoable before any P1/P2 work starts |
| Ambiguous spec details implemented inconsistently across modules | Medium | Medium | REQUIREMENTS.md's Ambiguities table is the single place assumptions are recorded; new ambiguities get added there before being coded around |
