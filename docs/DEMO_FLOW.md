# DEMO FLOW — PeoplePay360

Two end-to-end scenarios, ~5 minutes total. Architecture is optimized so both
of these are fully real (no mocked step) — see RISKS.md for what could break
them.

## Demo 1 — Employee to Payslip (Centerpiece, 0.41)

1. Open Employee **Arjun Mehta** — show Department (Engineering), Position, Manager (Priya Sharma).
2. Show his Working Schedule (Mon–Fri 09:00–17:00, 30 min break -> 37.5 hrs/week, derived not stored).
3. Show his historical Contracts (e.g. a prior EXPIRED contract + current ACTIVE one) — point out dates.
4. Run `getApplicableContract` conceptually: show it resolves to the contract covering the demo payroll period, not just "whatever's newest."
5. Show his Attendance for the period (a normal mix, maybe one LATE, one OVERTIME).
6. Show the Salary Structure "Regular Salary" and open its Salary Rules, showing sequence 10→70.
7. Start a **new Payrun**: Step 1 — select "Regular Salary" + the demo period → Continue (no Payrun created yet).
8. Step 2 — eligible employees list appears; select Arjun (+ others) → **Create Payrun** (now persisted, status DRAFT).
9. **Compute** — Payslip(s) generated; show Basic / Allowances / Gross / Deductions / Net breakdown per PayslipLine.
10. Show any warnings (e.g. a deliberately-seeded missing-bank-details employee to prove warnings are real).
11. **Validate** the Payrun (blocked until ERROR-level warnings are cleared — demonstrate the guard on the seeded warning employee, then fix and retry).
12. **Mark Paid**.
13. Generate the **Payslip PDF** for Arjun.
14. Open the **Dashboard** — show the numbers just changed because of this exact Payrun (net paid total ticks up, payslip count increments) — proving it's live data, not a static chart.

## Demo 2 — Leave Flow (0.42)

1. Show/create a **Time Off Type** (e.g. "Annual Leave", unit = DAYS, requires_allocation = true, requires_approval = true).
2. **Allocate** e.g. 18 days to an employee for the current validity year.
3. Log in as (or simulate) that **Employee**, create a **Time Off Request** for a few days within the period.
4. Switch to HR view — request shows **PENDING**.
5. **Approve** it.
6. Show the allocation's derived balance: `allocated - taken = remaining` dropped by exactly the request's duration.
7. Attempt to approve a second overlapping/over-limit request → show the balance guard rejecting it (proves the check is real, not decorative).
8. (If time) show approved leave reflected in the employee's attendance/period context feeding into worked-days for payroll.

## Representative Seed Data (0.43 — Documented, Not Implemented)

| Entity | Values |
|---|---|
| Department | Engineering |
| Employee | Arjun Mehta, employee_number EMP-1001, join_date within the last 2 years |
| Manager | Priya Sharma (separate Employee record, no manager of her own) |
| Working Schedule | "Standard 5-Day", Mon–Fri 09:00–17:00, 30 min break/day -> 37.5 hrs/week |
| Contract (historical) | e.g. 1 prior EXPIRED contract (lower wage) + 1 current ACTIVE contract covering the demo payroll period, wage = 30,000 |
| Salary Structure | "Regular Salary" |
| Salary Rules | BASIC (FIXED 30000, prorate), HRA (PERCENTAGE 40% of BASIC), TRANSPORT (FIXED 2000), GROSS (FORMULA BASIC+HRA+TRANSPORT), TAX (PERCENTAGE 10% of GROSS), OTHER_DEDUCTION (FIXED 500), NET (FORMULA GROSS-TAX-OTHER_DEDUCTION) |
| Time Off Type | "Annual Leave", DAYS, requires_allocation=true |
| Allocation | 18 days, validity = current year |
| Deliberate warning case | one seeded employee with missing bank details, to prove the validation matrix is real |

Exact currency amounts are illustrative and will be finalized in Phase 12
(seed data + polish) — not adjusted merely for cosmetic effect (0.43).
