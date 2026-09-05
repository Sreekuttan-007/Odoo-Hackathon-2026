from pydantic import BaseModel, model_validator
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal
from app.models.payroll import RuleCategory, ComputationMethod, PayrunStatus, WarningSeverity
from app.schemas.employee import EmployeeMinimal


# ------------------------------------------------------------- Structures --

class SalaryStructureBase(BaseModel):
    name: str
    code: Optional[str] = None
    description: Optional[str] = None
    is_active: bool = True


class SalaryStructureCreate(SalaryStructureBase):
    pass


class SalaryStructureUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class SalaryStructureResponse(SalaryStructureBase):
    id: int
    rule_count: int = 0
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SalaryStructureMinimal(BaseModel):
    id: int
    name: str
    is_active: bool

    class Config:
        from_attributes = True


# ------------------------------------------------------------------ Rules --

class SalaryRuleBase(BaseModel):
    name: str
    code: str
    category: RuleCategory
    sequence: int = 10
    computation_method: ComputationMethod
    fixed_amount: Optional[Decimal] = None
    percentage: Optional[Decimal] = None
    percentage_base: Optional[str] = None
    formula_expression: Optional[str] = None
    quantity: Decimal = Decimal(1)
    is_active: bool = True

    @model_validator(mode="after")
    def validate_method_fields(self):
        if self.computation_method == ComputationMethod.FIXED and self.fixed_amount is None:
            raise ValueError("fixed_amount is required for FIXED rules")
        if self.computation_method == ComputationMethod.PERCENTAGE and (self.percentage is None or not self.percentage_base):
            raise ValueError("percentage and percentage_base are required for PERCENTAGE rules")
        if self.computation_method == ComputationMethod.FORMULA and not self.formula_expression:
            raise ValueError("formula_expression is required for FORMULA rules")
        return self


class SalaryRuleCreate(SalaryRuleBase):
    pass


class SalaryRuleUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    category: Optional[RuleCategory] = None
    sequence: Optional[int] = None
    computation_method: Optional[ComputationMethod] = None
    fixed_amount: Optional[Decimal] = None
    percentage: Optional[Decimal] = None
    percentage_base: Optional[str] = None
    formula_expression: Optional[str] = None
    quantity: Optional[Decimal] = None
    is_active: Optional[bool] = None


class SalaryRuleResponse(SalaryRuleBase):
    id: int
    salary_structure_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SalaryStructureDetailResponse(SalaryStructureResponse):
    rules: List[SalaryRuleResponse] = []


# ----------------------------------------------------------------- Payrun --

class EligibleEmployee(BaseModel):
    employee: EmployeeMinimal
    eligible: bool
    reason: Optional[str] = None
    working_schedule_summary: Optional[str] = None
    wage_monthly: Optional[Decimal] = None


class PayrunCreate(BaseModel):
    salary_structure_id: int
    period_start: date
    period_end: date
    employee_ids: List[int]

    @model_validator(mode="after")
    def validate_fields(self):
        if self.period_end < self.period_start:
            raise ValueError("period_end must be on or after period_start")
        if not self.employee_ids:
            raise ValueError("At least one employee must be selected")
        return self


class PayrunResponse(BaseModel):
    id: int
    reference: str
    salary_structure: SalaryStructureMinimal
    period_start: date
    period_end: date
    status: PayrunStatus
    employee_count: int
    total_gross: Decimal
    total_net: Decimal
    warning_count: int
    created_by_name: Optional[str] = None
    computed_at: Optional[datetime] = None
    validated_at: Optional[datetime] = None
    validated_by_name: Optional[str] = None
    paid_at: Optional[datetime] = None
    paid_by_name: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ValidationBlockerDetail(BaseModel):
    payslip_id: int
    employee: EmployeeMinimal
    messages: List[str]


# ---------------------------------------------------------------- Payslip --

class PayslipLineResponse(BaseModel):
    id: int
    rule_name_snapshot: str
    rule_code_snapshot: str
    category_snapshot: RuleCategory
    sequence_snapshot: int
    computation_method_snapshot: ComputationMethod
    base_description_snapshot: Optional[str] = None
    amount: Decimal
    quantity: Optional[Decimal] = None

    class Config:
        from_attributes = True


class PayrollWarningResponse(BaseModel):
    id: int
    severity: WarningSeverity
    code: str
    message: str

    class Config:
        from_attributes = True


class PayslipResponse(BaseModel):
    id: int
    payrun_id: int
    payrun_reference: str
    employee: EmployeeMinimal
    contract_id: Optional[int] = None
    salary_structure: SalaryStructureMinimal
    period_start: date
    period_end: date
    status: PayrunStatus
    worked_days: Optional[Decimal] = None
    expected_work_days: Optional[Decimal] = None
    worked_hours: Optional[Decimal] = None
    basic: Decimal
    allowances: Decimal
    gross: Decimal
    deductions: Decimal
    net: Decimal
    warning_count: int
    lines: List[PayslipLineResponse] = []
    warnings: List[PayrollWarningResponse] = []
    computed_at: Optional[datetime] = None
    validated_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PayslipSummaryResponse(BaseModel):
    id: int
    payrun_id: int
    employee: EmployeeMinimal
    salary_structure: SalaryStructureMinimal
    period_start: date
    period_end: date
    status: PayrunStatus
    basic: Decimal
    gross: Decimal
    net: Decimal
    warning_count: int

    class Config:
        from_attributes = True
