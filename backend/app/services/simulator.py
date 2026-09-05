"""Payroll Simulator (Phase 9): a deterministic what-if engine built
entirely on the canonical payroll engine (build_calculation_context +
execute_rules, both in payroll_engine.py). This is NOT a second payroll
calculator — every number here comes from the exact same rule-execution
function that produces real, persisted Payslips.

SIMULATE, DO NOT MUTATE — the absolute invariant of this module:
- Overridden rules are represented as transient SalaryRule instances that
  are never passed to `db.add()` — plain Python objects the SQLAlchemy
  session never tracks. There is no code path in this module that can
  write them to the database, by construction, not by convention.
- No Payrun, Payslip, or PayslipLine is ever created here.
- The real (non-overridden) SalaryRule rows loaded from `structure.rules`
  are read-only in every code path below — never assigned to, only read.
"""
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Optional
from sqlalchemy.orm import Session
from app.models.employee import Employee
from app.models.payroll import SalaryStructure, SalaryRule
from app.services import payroll_engine


class InvalidOverrideError(ValueError):
    pass


@dataclass
class RuleOverride:
    rule_id: int
    computation_method: Optional[str] = None
    fixed_amount: Optional[Decimal] = None
    percentage: Optional[Decimal] = None
    base_code: Optional[str] = None
    formula_expression: Optional[str] = None
    quantity: Optional[Decimal] = None


@dataclass
class EmployeeScenario:
    employee: Employee
    excluded: bool
    exclusion_code: Optional[str]
    exclusion_reason: Optional[str]
    current_lines: list = field(default_factory=list)
    current_categories: dict = field(default_factory=dict)
    simulated_lines: list = field(default_factory=list)
    simulated_categories: dict = field(default_factory=dict)


def resolve_overrides(structure: SalaryStructure, raw_overrides: list) -> dict[int, RuleOverride]:
    """Validates every override's rule_id actually belongs to this Salary
    Structure before anything else runs — never trust the frontend's
    selection. Raises InvalidOverrideError (mapped to 400 by the route)
    on any rule_id that doesn't belong here."""
    valid_ids = {r.id for r in structure.rules}
    resolved: dict[int, RuleOverride] = {}
    for o in raw_overrides:
        if o.rule_id not in valid_ids:
            raise InvalidOverrideError(f"Rule {o.rule_id} does not belong to Salary Structure {structure.id}.")
        resolved[o.rule_id] = RuleOverride(
            rule_id=o.rule_id, computation_method=o.computation_method, fixed_amount=o.fixed_amount,
            percentage=o.percentage, base_code=o.base_code, formula_expression=o.formula_expression,
            quantity=o.quantity,
        )
    return resolved


def build_effective_rules(structure_rules: list[SalaryRule], overrides: dict[int, RuleOverride]) -> list[SalaryRule]:
    """Real active rules, in the same order/filtering as the real engine
    (payroll_engine.active_structure_rules), with any overridden rule
    replaced by a transient SalaryRule carrying the temporary values.

    That transient object is a plain SQLAlchemy-mapped instance that is
    never added to a Session (no db.add(), no db.merge()) — it exists only
    in this request's memory and is discarded when the request ends. It
    cannot be flushed or committed because nothing ever hands it to a
    session in the first place."""
    effective = []
    for rule in payroll_engine.active_structure_rules(structure_rules):
        override = overrides.get(rule.id)
        if override is None:
            effective.append(rule)
            continue
        effective.append(SalaryRule(
            id=rule.id,
            salary_structure_id=rule.salary_structure_id,
            name=rule.name,
            code=rule.code,
            category=rule.category,
            sequence=rule.sequence,
            computation_method=override.computation_method or rule.computation_method,
            fixed_amount=override.fixed_amount if override.fixed_amount is not None else rule.fixed_amount,
            percentage=override.percentage if override.percentage is not None else rule.percentage,
            percentage_base=override.base_code if override.base_code is not None else rule.percentage_base,
            formula_expression=override.formula_expression if override.formula_expression is not None else rule.formula_expression,
            quantity=override.quantity if override.quantity is not None else rule.quantity,
            is_active=True,
        ))
    return effective


def simulate_employee(
    db: Session, employee: Employee, period_start: date, period_end: date,
    current_rules: list[SalaryRule], simulated_rules: list[SalaryRule],
) -> EmployeeScenario:
    """Runs both the real (current_rules) and hypothetical (simulated_rules)
    rule sets for one employee, sharing a single build_calculation_context()
    call between them — one attendance/time-off query pair per employee,
    not one per rule set, regardless of how many overrides are in play.

    Uses the exact same eligibility check a real Payrun would use
    (payroll_engine.check_eligibility, no exclude_payrun_id — a genuine
    overlapping Payslip correctly excludes the employee here too, exactly
    as it would block a real Payrun for this period)."""
    eligibility = payroll_engine.check_eligibility(db, employee, period_start, period_end)
    if not eligibility.eligible or eligibility.contract is None:
        return EmployeeScenario(employee=employee, excluded=True, exclusion_code=eligibility.code, exclusion_reason=eligibility.reason)

    base_context = payroll_engine.build_calculation_context(db, employee, eligibility.contract, period_start, period_end)
    current_lines, current_categories, _ = payroll_engine.execute_rules(current_rules, base_context)
    simulated_lines, simulated_categories, _ = payroll_engine.execute_rules(simulated_rules, base_context)

    return EmployeeScenario(
        employee=employee, excluded=False, exclusion_code=None, exclusion_reason=None,
        current_lines=current_lines, current_categories=current_categories,
        simulated_lines=simulated_lines, simulated_categories=simulated_categories,
    )


def is_monthly_period(period_start: date, period_end: date) -> bool:
    """Heuristic for "this scenario looks like one calendar month" — used
    only to decide whether to show an annualized estimate, never to alter
    the calculation itself."""
    return 28 <= (period_end - period_start).days + 1 <= 31
