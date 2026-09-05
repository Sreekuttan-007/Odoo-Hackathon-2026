# SALARY RULE ENGINE — PeoplePay360

This is the core differentiator of the project (0.17). Salary Rules must
*actually drive* payslip numbers — never a static config screen with a
hardcoded net pay behind it.

## Categories

`BASIC`, `ALLOWANCE`, `GROSS`, `DEDUCTION`, `NET` — as specified in 0.17.
Category is descriptive/reporting metadata (drives payslip section grouping)
and does not itself change how a rule computes; `computation_type` does that.

## Computation Types

### FIXED
`value_config = { amount: number }`. Result is a constant, optionally
prorated by worked days (see "Proration" below).

### PERCENTAGE
`value_config = { percentOf: ruleCode, percent: number }`. Result =
`percent/100 * context[percentOf]`. `percentOf` must reference a rule
`code` that has **already executed** in the current structure's sequence
(enforced at structure-save time, not at compute time, so a broken reference
is caught early — see Validation below).

### FORMULA
`value_config = { expression: string }`. A constrained expression string,
e.g. `"BASIC * 0.4 + TRANSPORT"`. Evaluated by a **safe, whitelisted
expression evaluator** — not `eval()`/`Function()` and not a general scripting
sandbox. The evaluator:
- allows only: numeric literals, `+ - * / ( )`, and identifiers that must
  match an already-computed rule `code` in the current context.
- rejects any identifier not present in the calculation context (undefined
  variable = compile-time error on the rule, not a runtime crash mid-payrun).
- has no access to function calls, object property access, loops, or I/O.

This satisfies 0.17's "safe and constrained expression system" requirement
without building a general-purpose interpreter.

## Sequence & Calculation Context (0.18)

Rules execute in ascending `sequence` order within a Salary Structure. The
engine threads a single mutable calculation context through the run:

```
context = {
    employee,
    contract,
    payrollPeriod,
    workedDays,
    attendanceSummary,
    leaveSummary,
    results: {}   # ruleCode -> computed amount, filled in as rules execute
}

function computePayslip(structure, context):
    orderedRules = SalaryStructureRule
        .where(salary_structure_id = structure.id)
        .orderBy(sequence)

    lines = []
    for rule in orderedRules:
        amount = executeSalaryRule(rule, context)
        context.results[rule.code] = amount
        lines.append({ rule_code: rule.code, category: rule.category,
                        sequence: rule.sequence, amount })
    return lines
```

`executeSalaryRule(rule, context)` dispatches on `computation_type`:

```
function executeSalaryRule(rule, context):
    switch rule.computation_type:
        case FIXED:      return prorate(rule.value_config.amount, context)
        case PERCENTAGE: return context.results[rule.value_config.percentOf] * rule.value_config.percent / 100
        case FORMULA:    return evaluateSafeExpression(rule.value_config.expression, context.results)
```

**A later rule can depend on an earlier one** (e.g. `GROSS` sums `BASIC +
ALLOWANCE`, `TAX` is a percentage of `GROSS`, `NET` = `GROSS - DEDUCTIONS`)
precisely because `context.results` accumulates as the loop progresses. A
rule referencing a `code` that has not executed yet (wrong sequencing) must
fail loudly at structure-configuration time / dry-run, not silently produce
`undefined`/`0`.

## Proration ("worked_days" input)

`FIXED` amounts (and, by extension, anything downstream in the chain) may be
prorated by worked days for partial periods (new hire mid-month, contract
ending mid-month):

```
prorate(amount, context) =
    amount * (context.workedDays / context.expectedWorkingDaysInPeriod)
```

Whether a given FIXED rule prorates is a per-rule flag in `value_config`
(`{ amount, prorate: true }`) — not every fixed rule should necessarily
prorate (e.g. a one-time flat bonus might not). Documented as a Phase 5/6
decision point, not resolved further here.

## Historical Stability (Invariant 5 & 0.24 test #19)

Once a Payslip is computed, its `PayslipLine` rows store the **snapshotted**
`rule_code`, `category`, `sequence`, and `amount` — they do not re-read the
live `SalaryRule` table. If a `SalaryRule`'s `value_config` changes next
month, only *future* payroll computations see the new configuration;
previously validated Payslips remain exactly as they were computed. This is
why `PayslipLine` denormalizes those fields rather than joining live to
`SalaryRule` (see DATABASE_SCHEMA.md).

## Worked Example (Documentation Only — Not Implemented)

| Seq | Code | Category | Type | Config | Result (example) |
|---|---|---|---|---|---|
| 10 | BASIC | BASIC | FIXED | `{amount: 30000, prorate: true}` | 30,000 |
| 20 | HRA | ALLOWANCE | PERCENTAGE | `{percentOf: "BASIC", percent: 40}` | 12,000 |
| 30 | TRANSPORT | ALLOWANCE | FIXED | `{amount: 2000}` | 2,000 |
| 40 | GROSS | GROSS | FORMULA | `"BASIC + HRA + TRANSPORT"` | 44,000 |
| 50 | TAX | DEDUCTION | PERCENTAGE | `{percentOf: "GROSS", percent: 10}` | 4,400 |
| 60 | OTHER_DEDUCTION | DEDUCTION | FIXED | `{amount: 500}` | 500 |
| 70 | NET | NET | FORMULA | `"GROSS - TAX - OTHER_DEDUCTION"` | 39,100 |

## Configuration-Time Validation (not runtime guessing)

When a Salary Structure/Rule is saved, the engine should be able to dry-run
validate that:
- every `PERCENTAGE.percentOf` and every identifier in a `FORMULA.expression`
  refers to a rule `code` present in the same structure at a **lower**
  sequence number.
- no rule `code` is duplicated within one structure.

This turns a broken configuration into an immediate, explainable error rather
than a mysterious wrong payslip discovered later.
