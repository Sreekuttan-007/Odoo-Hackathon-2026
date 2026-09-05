# PAYROLL ENGINE — PeoplePay360

## Module Layout (0.19)

```
backend/src/payroll/
    contractSelection.ts   # getApplicableContract, conflict detection
    ruleEngine.ts           # executeSalaryRule, expression evaluator, computePayslipLines
    payrollCalculation.ts   # calculateWorkedDays, getEligibleEmployees, computePayrun orchestration
    validation.ts           # validateEmployeePayrollData, validatePayslip, the warning matrix
    payslipGeneration.ts    # computePayslip (ties contract + rules + context together), detectDuplicatePayslip
```

These are plain functions operating on data passed in — no framework
decorators, no hidden DI. `services/payrollService.ts` is the only caller of
this module from the API layer.

## Core Functions (Signatures, No Implementation)

| Function | Responsibility |
|---|---|
| `getApplicableContract(employee, payrollPeriod)` | see CONTRACT_RULES.md |
| `getEligibleEmployees(salaryStructure, payrollPeriod)` | active employees with a resolvable, non-conflicting applicable contract for the period; used for Payrun Step 2 |
| `validateEmployeePayrollData(employee, contract)` | checks bank details present, contract resolvable/non-conflicting, employee active |
| `calculateWorkedDays(employee, payrollPeriod, contract)` | derives worked days from Attendance + approved paid Time Off, bounded by the contract's own start/end within the period (proration input) |
| `executeSalaryRule(rule, context)` | see SALARY_RULE_ENGINE.md |
| `computePayslip(employee, payrun)` | orchestrates: resolve contract -> build context -> run rule engine -> persist Payslip + PayslipLines |
| `detectDuplicatePayslip(employee, payrun)` | checks the `(employee_id, payrun_id)` unique constraint pre-insert; used by `computePayslip`'s upsert logic |
| `validatePayslip(payslip)` | runs the full Validation Matrix below, returns list of `PayrollWarning` |
| `markPayrunPaid(payrun)` | guard: payrun.status == VALIDATED; sets PAID; does not touch PayslipLine data |

## Calculation Context (repeated from SALARY_RULE_ENGINE.md for completeness)

```
context = {
  employee, contract, payrollPeriod,
  workedDays, attendanceSummary, leaveSummary,
  results: {}   # filled progressively as rules execute
}
```

Built once per employee per Compute call, then threaded through
`computePayslipLines`.

## Payroll Validation Matrix (Section I)

| Condition | Severity | Message | Blocks Validation? |
|---|---|---|---|
| No applicable Contract for period | ERROR | "No contract covers this payroll period" | Yes |
| Conflicting ACTIVE contracts | ERROR | "Employee has overlapping active contracts" | Yes |
| Missing bank details | WARNING (ERROR only at Mark Paid step) | "Employee is missing bank account details" | Blocks **Mark Paid**, not Validate |
| Duplicate Payslip detected for employee+payrun | ERROR | "A payslip already exists for this employee in this payrun" | Yes (prevents re-creation; Compute instead updates the existing one, see PAYRUN_STATE_MACHINE.md) |
| Missing/inactive Salary Structure | ERROR | "Selected salary structure is missing or inactive" | Yes |
| Salary Structure has zero rules | ERROR | "Salary structure has no salary rules configured" | Yes |
| Salary rule references undefined identifier (bad FORMULA/PERCENTAGE config) | ERROR | "Salary rule '<code>' references an unknown rule '<ref>'" | Yes |
| Employee inactive/terminated during period | WARNING | "Employee is inactive for part of this period" | No (informational; worked days already prorated) |
| Attendance anomaly (unexplained absences, many MISSING_CHECK_OUT days) | WARNING | "Employee has N unresolved attendance exceptions this period" | No |
| Contract changed mid-period (see CONTRACT_RULES.md) | WARNING | "Employee's contract changed during this period" | No |
| Negative or zero computed NET | ERROR | "Computed net salary is zero or negative" | Yes |

`ERROR` severity always sets `blocks_validation = true`; `WARNING` and `INFO`
never block Validate on their own, but WARNING items tied to payment (bank
details) block the later **Mark Paid** action specifically. This distinction
(0.25) is why `PayrollWarning` carries both a `severity` and a
`blocks_validation` flag rather than inferring blocking purely from severity.

## Where PDF/Email Fit

`payslipGeneration.ts` produces the computed data only. A separate
`integrations/pdfService.ts` takes an already-computed, already-validated
Payslip and renders it — it has no payroll logic and cannot change numbers.
`integrations/emailService.ts` takes already-generated PDFs and sends them;
its failures are logged as delivery warnings and never roll back or mutate
Payrun/Payslip state (0.30).
