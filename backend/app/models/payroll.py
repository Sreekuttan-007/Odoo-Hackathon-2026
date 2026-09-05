from sqlalchemy import (
    Column, Integer, String, DateTime, Date, ForeignKey, Numeric, Text,
    Boolean, Enum, UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base
import enum


class RuleCategory(str, enum.Enum):
    BASIC = "BASIC"
    ALLOWANCE = "ALLOWANCE"
    GROSS = "GROSS"
    DEDUCTION = "DEDUCTION"
    NET = "NET"


class ComputationMethod(str, enum.Enum):
    FIXED = "FIXED"
    PERCENTAGE = "PERCENTAGE"
    FORMULA = "FORMULA"


class PayrunStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    COMPUTED = "COMPUTED"
    VALIDATED = "VALIDATED"
    PAID = "PAID"


class WarningSeverity(str, enum.Enum):
    BLOCKER = "BLOCKER"
    WARNING = "WARNING"
    INFO = "INFO"


class SalaryStructure(Base):
    __tablename__ = "salary_structures"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    code = Column(String, unique=True, index=True, nullable=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    rules = relationship(
        "SalaryRule", back_populates="structure",
        order_by="SalaryRule.sequence", cascade="all, delete-orphan",
    )


class SalaryRule(Base):
    __tablename__ = "salary_rules"
    __table_args__ = (UniqueConstraint("salary_structure_id", "code", name="uq_salary_rule_structure_code"),)

    id = Column(Integer, primary_key=True, index=True)
    salary_structure_id = Column(Integer, ForeignKey("salary_structures.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    code = Column(String, nullable=False)
    category = Column(Enum(RuleCategory), nullable=False)
    sequence = Column(Integer, nullable=False, default=10)
    computation_method = Column(Enum(ComputationMethod), nullable=False)

    fixed_amount = Column(Numeric(12, 2), nullable=True)
    percentage = Column(Numeric(6, 2), nullable=True)
    # "CONTRACT_WAGE" or an earlier rule's code within the same structure.
    percentage_base = Column(String, nullable=True)
    formula_expression = Column(Text, nullable=True)
    quantity = Column(Numeric(6, 2), nullable=False, default=1)

    is_active = Column(Boolean, nullable=False, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    structure = relationship("SalaryStructure", back_populates="rules")


class Payrun(Base):
    __tablename__ = "payruns"

    id = Column(Integer, primary_key=True, index=True)
    reference = Column(String, unique=True, index=True, nullable=False)
    salary_structure_id = Column(Integer, ForeignKey("salary_structures.id"), nullable=False)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    status = Column(Enum(PayrunStatus), nullable=False, default=PayrunStatus.DRAFT)

    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    computed_at = Column(DateTime(timezone=True), nullable=True)
    validated_at = Column(DateTime(timezone=True), nullable=True)
    validated_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    paid_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    salary_structure = relationship("SalaryStructure", foreign_keys=[salary_structure_id])
    created_by = relationship("User", foreign_keys=[created_by_user_id])
    validated_by = relationship("User", foreign_keys=[validated_by_user_id])
    paid_by = relationship("User", foreign_keys=[paid_by_user_id])
    payslips = relationship("Payslip", back_populates="payrun", cascade="all, delete-orphan")


class Payslip(Base):
    __tablename__ = "payslips"
    __table_args__ = (UniqueConstraint("payrun_id", "employee_id", name="uq_payslip_payrun_employee"),)

    id = Column(Integer, primary_key=True, index=True)
    payrun_id = Column(Integer, ForeignKey("payruns.id"), nullable=False, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=True)
    salary_structure_id = Column(Integer, ForeignKey("salary_structures.id"), nullable=False)

    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    status = Column(Enum(PayrunStatus), nullable=False, default=PayrunStatus.DRAFT)

    worked_days = Column(Numeric(6, 2), nullable=True)
    expected_work_days = Column(Numeric(6, 2), nullable=True)
    worked_hours = Column(Numeric(8, 2), nullable=True)

    basic = Column(Numeric(12, 2), nullable=False, default=0)
    allowances = Column(Numeric(12, 2), nullable=False, default=0)
    gross = Column(Numeric(12, 2), nullable=False, default=0)
    deductions = Column(Numeric(12, 2), nullable=False, default=0)
    net = Column(Numeric(12, 2), nullable=False, default=0)
    warning_count = Column(Integer, nullable=False, default=0)

    computed_at = Column(DateTime(timezone=True), nullable=True)
    validated_at = Column(DateTime(timezone=True), nullable=True)
    paid_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    employee = relationship("Employee", foreign_keys=[employee_id])
    contract = relationship("Contract", foreign_keys=[contract_id])
    salary_structure = relationship("SalaryStructure", foreign_keys=[salary_structure_id])
    payrun = relationship("Payrun", back_populates="payslips")
    lines = relationship(
        "PayslipLine", back_populates="payslip",
        order_by="PayslipLine.sequence_snapshot", cascade="all, delete-orphan",
    )
    warnings = relationship("PayrollWarning", back_populates="payslip", cascade="all, delete-orphan")


class PayslipLine(Base):
    __tablename__ = "payslip_lines"

    id = Column(Integer, primary_key=True, index=True)
    payslip_id = Column(Integer, ForeignKey("payslips.id"), nullable=False, index=True)
    salary_rule_id = Column(Integer, ForeignKey("salary_rules.id"), nullable=True)

    rule_name_snapshot = Column(String, nullable=False)
    rule_code_snapshot = Column(String, nullable=False)
    category_snapshot = Column(Enum(RuleCategory), nullable=False)
    sequence_snapshot = Column(Integer, nullable=False)
    computation_method_snapshot = Column(Enum(ComputationMethod), nullable=False)
    base_description_snapshot = Column(String, nullable=True)

    # Structured PayTrace metadata (Phase 7) — captured at compute time
    # alongside base_description_snapshot's human string, so a historical
    # trace can be rebuilt without touching the (possibly since-edited)
    # SalaryRule row or Contract. Null on lines computed before Phase 7;
    # PayTrace falls back to base_description_snapshot only for those.
    fixed_amount_snapshot = Column(Numeric(12, 2), nullable=True)
    percentage_snapshot = Column(Numeric(6, 2), nullable=True)
    base_code_snapshot = Column(String, nullable=True)  # "CONTRACT_WAGE" or another rule's code
    base_amount_snapshot = Column(Numeric(14, 4), nullable=True)  # resolved value of base_code_snapshot at compute time
    formula_inputs_snapshot = Column(Text, nullable=True)  # JSON: {identifier: "value"} referenced by the formula

    amount = Column(Numeric(12, 2), nullable=False)
    quantity = Column(Numeric(6, 2), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    payslip = relationship("Payslip", back_populates="lines")
    salary_rule = relationship("SalaryRule", foreign_keys=[salary_rule_id])


class PayrollWarning(Base):
    __tablename__ = "payroll_warnings"

    id = Column(Integer, primary_key=True, index=True)
    payslip_id = Column(Integer, ForeignKey("payslips.id"), nullable=False, index=True)
    severity = Column(Enum(WarningSeverity), nullable=False)
    code = Column(String, nullable=False)
    message = Column(Text, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    payslip = relationship("Payslip", back_populates="warnings")
