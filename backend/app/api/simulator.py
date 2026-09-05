"""Payroll Simulator (Phase 9) — a read-only what-if endpoint. See
app/services/simulator.py for the SIMULATE, DO NOT MUTATE invariant this
whole module is built around: nothing here writes to SalaryRule,
SalaryStructure, Contract, Employee, Payrun, Payslip, or PayslipLine."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.user import User
from app.models.employee import Employee
from app.models.payroll import SalaryStructure
from app.schemas.simulator import (
    SimulatorRunRequest, SimulatorRunResponse, EmployeeSimulationResult,
    ScenarioTotals, SimulatedLine, AggregateImpact,
)
from decimal import Decimal, ROUND_HALF_UP
from app.api.deps import get_current_payroll_manager
from app.services import simulator, payroll_engine

router = APIRouter()


def _totals(categories: dict) -> ScenarioTotals:
    return ScenarioTotals(
        basic=categories.get("BASIC", 0), allowances=categories.get("ALLOWANCE", 0),
        gross=categories.get("GROSS", 0), deductions=categories.get("DEDUCTION", 0),
        net=categories.get("NET", 0),
    )


def _components(current_lines: list, simulated_lines: list) -> list[SimulatedLine]:
    current_by_code = {cl.rule.code: cl for cl in current_lines}
    simulated_by_code = {cl.rule.code: cl for cl in simulated_lines}
    all_codes = list(dict.fromkeys([cl.rule.code for cl in current_lines] + [cl.rule.code for cl in simulated_lines]))
    lines = []
    for code in all_codes:
        cur = current_by_code.get(code)
        sim = simulated_by_code.get(code)
        source = sim or cur
        current_amount = cur.result.amount if cur else None
        simulated_amount = sim.result.amount if sim else None
        lines.append(SimulatedLine(
            rule_code=code, rule_name=source.rule.name, category=source.rule.category,
            sequence=source.rule.sequence, method=source.rule.computation_method,
            current_amount=current_amount, simulated_amount=simulated_amount,
            changed=(current_amount != simulated_amount),
        ))
    return sorted(lines, key=lambda l: l.sequence)


@router.post("/payroll/simulator/run", response_model=SimulatorRunResponse)
def run_simulator(
    payload: SimulatorRunRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_payroll_manager),
):
    if not payload.employee_ids:
        raise HTTPException(400, detail={"error": {"code": "NO_EMPLOYEES_SELECTED", "message": "At least one employee must be selected."}})
    if payload.period_end < payload.period_start:
        raise HTTPException(400, detail={"error": {"code": "INVALID_PERIOD", "message": "period_end must be on or after period_start."}})

    structure = db.query(SalaryStructure).filter(SalaryStructure.id == payload.salary_structure_id).first()
    if not structure:
        raise HTTPException(404, detail={"error": {"code": "NOT_FOUND", "message": "Salary structure not found."}})

    try:
        overrides = simulator.resolve_overrides(structure, payload.rule_overrides)
    except simulator.InvalidOverrideError as exc:
        raise HTTPException(400, detail={"error": {"code": "INVALID_OVERRIDE", "message": str(exc)}})

    current_rules = payroll_engine.active_structure_rules(structure.rules)
    simulated_rules = simulator.build_effective_rules(structure.rules, overrides)

    # Backend re-validates the employee list — never trusts the frontend's
    # selection. Employees that genuinely don't exist are silently dropped
    # from "selected" the same way an invalid id anywhere else in this API
    # would be, rather than fabricating a result for them.
    employees = db.query(Employee).filter(Employee.id.in_(payload.employee_ids)).all()

    results: list[EmployeeSimulationResult] = []
    total_current_gross = total_simulated_gross = 0
    total_current_deductions = total_simulated_deductions = 0
    total_current_net = total_simulated_net = 0
    increased = decreased = unchanged = 0
    simulated_count = 0

    for employee in employees:
        scenario = simulator.simulate_employee(db, employee, payload.period_start, payload.period_end, current_rules, simulated_rules)
        department_name = employee.department.name if employee.department else None
        employee_name = f"{employee.first_name} {employee.last_name}"

        if scenario.excluded:
            results.append(EmployeeSimulationResult(
                employee_id=employee.id, employee_name=employee_name, department=department_name,
                excluded=True, exclusion_code=scenario.exclusion_code, exclusion_reason=scenario.exclusion_reason,
                status="EXCLUDED",
            ))
            continue

        simulated_count += 1
        current_totals = _totals(scenario.current_categories)
        simulated_totals = _totals(scenario.simulated_categories)
        delta_net = simulated_totals.net - current_totals.net
        delta_net_percent = (
            (delta_net / current_totals.net * 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            if current_totals.net else None
        )

        if delta_net > 0:
            status_, increased = "INCREASED", increased + 1
        elif delta_net < 0:
            status_, decreased = "DECREASED", decreased + 1
        else:
            status_, unchanged = "UNCHANGED", unchanged + 1

        total_current_gross += current_totals.gross
        total_simulated_gross += simulated_totals.gross
        total_current_deductions += current_totals.deductions
        total_simulated_deductions += simulated_totals.deductions
        total_current_net += current_totals.net
        total_simulated_net += simulated_totals.net

        results.append(EmployeeSimulationResult(
            employee_id=employee.id, employee_name=employee_name, department=department_name,
            excluded=False, current=current_totals, simulated=simulated_totals,
            delta_gross=simulated_totals.gross - current_totals.gross,
            delta_deductions=simulated_totals.deductions - current_totals.deductions,
            delta_net=delta_net, delta_net_percent=delta_net_percent, status=status_,
            components=_components(scenario.current_lines, scenario.simulated_lines),
        ))

    delta_net_total = total_simulated_net - total_current_net
    monthly = simulator.is_monthly_period(payload.period_start, payload.period_end)

    return SimulatorRunResponse(
        salary_structure_id=structure.id, salary_structure_name=structure.name,
        period_start=payload.period_start, period_end=payload.period_end,
        employees_selected=len(payload.employee_ids), employees_simulated=simulated_count,
        employees_excluded=len(results) - simulated_count,
        aggregate=AggregateImpact(
            current_total_gross=total_current_gross, simulated_total_gross=total_simulated_gross,
            delta_gross=total_simulated_gross - total_current_gross,
            current_total_deductions=total_current_deductions, simulated_total_deductions=total_simulated_deductions,
            delta_deductions=total_simulated_deductions - total_current_deductions,
            current_total_net=total_current_net, simulated_total_net=total_simulated_net,
            delta_net=delta_net_total,
            employees_increased=increased, employees_decreased=decreased, employees_unchanged=unchanged,
            is_monthly_period=monthly,
            annualized_net_delta_estimate=(delta_net_total * 12) if monthly else None,
        ),
        employees=results,
    )
