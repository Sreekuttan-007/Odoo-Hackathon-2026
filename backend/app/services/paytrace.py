"""PayTrace (Phase 7): a deterministic explanation layer over already-
computed, persisted Payslip data.

This module NEVER recomputes payroll and NEVER touches the (possibly
since-edited) SalaryRule or Contract rows for historical values — it only
reads what was snapshotted onto PayslipLine at compute time. That's the
whole point: a payslip computed in September with HRA=20% must still show
20% here even if HRA is edited to 25% afterward. See payroll_engine.py's
compute_payslip for where these snapshots are written.

Lines computed before Phase 7 won't have the new structured snapshot
fields (fixed_amount_snapshot, percentage_snapshot, base_code_snapshot,
base_amount_snapshot, formula_inputs_snapshot) — those are None, and this
module falls back to the pre-existing base_description_snapshot string
rather than fabricating structured numbers it doesn't actually have.
"""
import json
from decimal import Decimal
from typing import Optional
from app.models.payroll import Payslip, PayslipLine, ComputationMethod, RuleCategory


def _d(value) -> str:
    return str(value) if value is not None else None


def _build_fixed_trace(line: PayslipLine) -> tuple[Optional[dict], Optional[str]]:
    if line.fixed_amount_snapshot is None:
        return None, None
    qty = line.quantity if line.quantity is not None else Decimal(1)
    calculation = {"fixed_amount": _d(line.fixed_amount_snapshot), "quantity": _d(qty)}
    if qty != 1:
        explanation = f"₹{line.fixed_amount_snapshot} × {qty} = ₹{line.amount}"
    else:
        explanation = f"Fixed amount of ₹{line.fixed_amount_snapshot}"
    return calculation, explanation


def _build_percentage_trace(line: PayslipLine) -> tuple[Optional[dict], Optional[str], Optional[str]]:
    if line.percentage_snapshot is None or line.base_amount_snapshot is None:
        return None, None, None
    base_label = "Contract Wage" if line.base_code_snapshot == "CONTRACT_WAGE" else line.base_code_snapshot
    calculation = {
        "percentage": _d(line.percentage_snapshot),
        "base_code": line.base_code_snapshot,
        "base_label": base_label,
        "base_amount": _d(line.base_amount_snapshot),
    }
    explanation = f"{line.percentage_snapshot}% of {base_label} (₹{line.base_amount_snapshot}) = ₹{line.amount}"
    depends_on = line.base_code_snapshot if line.base_code_snapshot != "CONTRACT_WAGE" else None
    return calculation, explanation, depends_on


def _build_formula_trace(line: PayslipLine) -> tuple[Optional[dict], Optional[str], list[str]]:
    if not line.formula_inputs_snapshot:
        return None, None, []
    try:
        inputs = json.loads(line.formula_inputs_snapshot)
    except (ValueError, TypeError):
        return None, None, []
    calculation = {"formula": line.base_description_snapshot, "inputs": inputs}
    explanation = f"{line.base_description_snapshot} = ₹{line.amount}"
    # Only rule-code inputs (not categories.* or context vars like contract_wage)
    # can be highlighted as a dependency on another trace entry.
    depends_on = [code for code in inputs if not code.startswith("categories.")]
    return calculation, explanation, depends_on


def build_trace_entry(line: PayslipLine, known_codes: set[str]) -> dict:
    calculation: Optional[dict] = None
    explanation: Optional[str] = None
    depends_on: list[str] = []

    if line.computation_method_snapshot == ComputationMethod.FIXED:
        calculation, explanation = _build_fixed_trace(line)
    elif line.computation_method_snapshot == ComputationMethod.PERCENTAGE:
        calculation, explanation, dep = _build_percentage_trace(line)
        if dep:
            depends_on = [dep]
    elif line.computation_method_snapshot == ComputationMethod.FORMULA:
        calculation, explanation, depends_on = _build_formula_trace(line)

    depends_on = [code for code in depends_on if code in known_codes]
    has_structured_history = calculation is not None

    return {
        "sequence": line.sequence_snapshot,
        "rule_name": line.rule_name_snapshot,
        "rule_code": line.rule_code_snapshot,
        "category": line.category_snapshot.value,
        "method": line.computation_method_snapshot.value,
        "quantity": _d(line.quantity),
        "result": _d(line.amount),
        "calculation": calculation,
        "explanation": explanation or line.base_description_snapshot or "",
        "depends_on": depends_on,
        "has_structured_history": has_structured_history,
    }


def _components(lines: list[PayslipLine], categories: set[RuleCategory]) -> list[dict]:
    return [
        {"rule_code": l.rule_code_snapshot, "rule_name": l.rule_name_snapshot, "amount": _d(l.amount)}
        for l in lines if l.category_snapshot in categories
    ]


def build_paytrace(payslip: Payslip) -> dict:
    """Returns a structured, deterministic explanation of one Payslip.
    Never raises for a normal payslip — an uncomputed or line-less payslip
    gets an `available: False` response instead of a fabricated trace."""
    if payslip.computed_at is None:
        return {
            "available": False,
            "reason": "NOT_COMPUTED",
            "message": "Payroll has not been computed yet.",
        }

    lines = sorted(payslip.lines, key=lambda l: l.sequence_snapshot)
    if not lines:
        return {
            "available": False,
            "reason": "NO_LINES",
            "message": "This payslip has no calculation lines to trace — it was blocked before any Salary Rule executed. See its warnings for why.",
        }

    known_codes = {l.rule_code_snapshot for l in lines}
    entries = [build_trace_entry(l, known_codes) for l in lines]

    contract = payslip.contract
    employee = payslip.employee

    return {
        "available": True,
        "employee": {
            "id": employee.id,
            "name": f"{employee.first_name} {employee.last_name}",
            "employee_code": employee.employee_code,
        },
        "period": {"start": payslip.period_start.isoformat(), "end": payslip.period_end.isoformat()},
        "salary_structure": {"id": payslip.salary_structure_id, "name": payslip.salary_structure.name},
        "contract": (
            {
                "reference": contract.reference,
                "wage_monthly": _d(contract.wage_monthly),
                "currency": contract.currency,
            }
            if contract else None
        ),
        "entries": entries,
        "aggregates": {
            "basic": _d(payslip.basic),
            "allowances": _d(payslip.allowances),
            "gross": _d(payslip.gross),
            "deductions": _d(payslip.deductions),
            "net": _d(payslip.net),
            "gross_components": _components(lines, {RuleCategory.BASIC, RuleCategory.ALLOWANCE}),
            "net_components": _components(lines, {RuleCategory.GROSS, RuleCategory.DEDUCTION}),
        },
    }
