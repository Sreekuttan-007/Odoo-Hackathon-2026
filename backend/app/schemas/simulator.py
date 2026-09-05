"""Payroll Simulator (Phase 9) request/response schemas.

The Simulator is read-only by construction: nothing in this module (or
the service/route behind it) ever writes to SalaryRule, SalaryStructure,
Contract, Employee, Payrun, Payslip, PayslipLine, or PayrollWarning."""
from pydantic import BaseModel
from typing import Optional, List
from datetime import date
from decimal import Decimal
from app.models.payroll import RuleCategory, ComputationMethod


class RuleOverrideIn(BaseModel):
    rule_id: int
    computation_method: Optional[ComputationMethod] = None
    fixed_amount: Optional[Decimal] = None
    percentage: Optional[Decimal] = None
    base_code: Optional[str] = None
    formula_expression: Optional[str] = None
    quantity: Optional[Decimal] = None


class SimulatorRunRequest(BaseModel):
    salary_structure_id: int
    period_start: date
    period_end: date
    employee_ids: List[int]
    rule_overrides: List[RuleOverrideIn] = []


class SimulatedLine(BaseModel):
    rule_code: str
    rule_name: str
    category: RuleCategory
    sequence: int
    method: ComputationMethod
    current_amount: Optional[Decimal] = None
    simulated_amount: Optional[Decimal] = None
    changed: bool


class ScenarioTotals(BaseModel):
    basic: Decimal
    allowances: Decimal
    gross: Decimal
    deductions: Decimal
    net: Decimal


class EmployeeSimulationResult(BaseModel):
    employee_id: int
    employee_name: str
    department: Optional[str] = None
    excluded: bool
    exclusion_code: Optional[str] = None
    exclusion_reason: Optional[str] = None
    current: Optional[ScenarioTotals] = None
    simulated: Optional[ScenarioTotals] = None
    delta_gross: Optional[Decimal] = None
    delta_deductions: Optional[Decimal] = None
    delta_net: Optional[Decimal] = None
    delta_net_percent: Optional[Decimal] = None
    status: str  # "INCREASED" | "DECREASED" | "UNCHANGED" | "EXCLUDED"
    components: List[SimulatedLine] = []


class AggregateImpact(BaseModel):
    current_total_gross: Decimal
    simulated_total_gross: Decimal
    delta_gross: Decimal
    current_total_deductions: Decimal
    simulated_total_deductions: Decimal
    delta_deductions: Decimal
    current_total_net: Decimal
    simulated_total_net: Decimal
    delta_net: Decimal
    employees_increased: int
    employees_decreased: int
    employees_unchanged: int
    is_monthly_period: bool
    annualized_net_delta_estimate: Optional[Decimal] = None


class SimulatorRunResponse(BaseModel):
    salary_structure_id: int
    salary_structure_name: str
    period_start: date
    period_end: date
    employees_selected: int
    employees_simulated: int
    employees_excluded: int
    aggregate: AggregateImpact
    employees: List[EmployeeSimulationResult]
