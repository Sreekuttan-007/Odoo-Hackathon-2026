from datetime import date, time
from decimal import Decimal
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.employee import Employee, EmployeeStatus
from app.models.department import Department
from app.models.job_position import JobPosition
from app.models.working_schedule import WorkingSchedule, WorkingScheduleLine, ScheduleStatus, DayOfWeek
from app.models.contract import Contract
from app.models.payroll import SalaryStructure, SalaryRule, Payrun, Payslip, RuleCategory, ComputationMethod, PayrunStatus
from app.services import payroll_engine

engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture()
def db():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def _setup_employee_with_contract(db, wage=Decimal(50000)):
    dept = Department(name="Engineering")
    pos = JobPosition(title="Software Engineer")
    db.add_all([dept, pos])
    db.commit()

    schedule = WorkingSchedule(name="40 Hours/Week", status=ScheduleStatus.ACTIVE)
    db.add(schedule)
    db.flush()
    for day in [DayOfWeek.MONDAY, DayOfWeek.TUESDAY, DayOfWeek.WEDNESDAY, DayOfWeek.THURSDAY, DayOfWeek.FRIDAY]:
        db.add(WorkingScheduleLine(working_schedule_id=schedule.id, day_of_week=day, start_time=time(9, 0), end_time=time(18, 0), break_minutes=60))
    db.commit()

    employee = Employee(first_name="Aarav", last_name="Mehta", status=EmployeeStatus.ACTIVE, working_schedule_id=schedule.id)
    db.add(employee)
    db.flush()

    contract = Contract(
        reference="CON/2026/0001", employee_id=employee.id, department_id=dept.id, job_position_id=pos.id,
        working_schedule_id=schedule.id, start_date=date(2026, 1, 1), end_date=None, wage_monthly=wage, currency="INR",
    )
    db.add(contract)
    db.commit()
    return employee, contract


def _canonical_structure(db):
    structure = SalaryStructure(name="Regular Salary", is_active=True)
    db.add(structure)
    db.flush()
    rules = [
        SalaryRule(salary_structure_id=structure.id, name="Basic Salary", code="BASIC", category=RuleCategory.BASIC,
                   sequence=1, computation_method=ComputationMethod.PERCENTAGE, percentage=Decimal(50), percentage_base="CONTRACT_WAGE"),
        SalaryRule(salary_structure_id=structure.id, name="House Rent Allowance", code="HRA", category=RuleCategory.ALLOWANCE,
                   sequence=10, computation_method=ComputationMethod.PERCENTAGE, percentage=Decimal(20), percentage_base="BASIC"),
        SalaryRule(salary_structure_id=structure.id, name="Standard Allowance", code="ALLOWANCE", category=RuleCategory.ALLOWANCE,
                   sequence=20, computation_method=ComputationMethod.FIXED, fixed_amount=Decimal(2000)),
        SalaryRule(salary_structure_id=structure.id, name="Gross Salary", code="GROSS", category=RuleCategory.GROSS,
                   sequence=60, computation_method=ComputationMethod.FORMULA, formula_expression='rules["BASIC"] + rules["HRA"] + rules["ALLOWANCE"]'),
        SalaryRule(salary_structure_id=structure.id, name="Provident Fund", code="PF", category=RuleCategory.DEDUCTION,
                   sequence=80, computation_method=ComputationMethod.PERCENTAGE, percentage=Decimal(10), percentage_base="BASIC"),
        SalaryRule(salary_structure_id=structure.id, name="Net Salary", code="NET", category=RuleCategory.NET,
                   sequence=100, computation_method=ComputationMethod.FORMULA, formula_expression='rules["GROSS"] - rules["PF"]'),
    ]
    db.add_all(rules)
    db.commit()
    return structure


def _payslip_for(db, employee, structure, period_start=date(2026, 2, 1), period_end=date(2026, 2, 28)):
    payrun = Payrun(reference="PR/2026/0001", salary_structure_id=structure.id, period_start=period_start, period_end=period_end, status=PayrunStatus.DRAFT)
    db.add(payrun)
    db.flush()
    payslip = Payslip(payrun_id=payrun.id, employee_id=employee.id, salary_structure_id=structure.id, period_start=period_start, period_end=period_end, status=PayrunStatus.DRAFT)
    db.add(payslip)
    db.commit()
    return payrun, payslip


def test_canonical_payroll_calculation(db):
    employee, contract = _setup_employee_with_contract(db, wage=Decimal(50000))
    structure = _canonical_structure(db)
    payrun, payslip = _payslip_for(db, employee, structure)

    payroll_engine.compute_payslip(db, payslip)
    db.commit()

    amounts = {l.rule_code_snapshot: l.amount for l in payslip.lines}
    assert amounts["BASIC"] == Decimal("25000.00")
    assert amounts["HRA"] == Decimal("5000.00")
    assert amounts["ALLOWANCE"] == Decimal("2000.00")
    assert amounts["GROSS"] == Decimal("32000.00")
    assert amounts["PF"] == Decimal("2500.00")
    assert amounts["NET"] == Decimal("29500.00")

    assert payslip.basic == Decimal("25000.00")
    assert payslip.allowances == Decimal("7000.00")
    assert payslip.gross == Decimal("32000.00")
    assert payslip.deductions == Decimal("2500.00")
    assert payslip.net == Decimal("29500.00")
    assert not payslip.warnings


def test_fixed_rule():
    from app.services.payroll_engine import _compute_rule_amount
    from types import SimpleNamespace
    rule = SimpleNamespace(computation_method=ComputationMethod.FIXED, fixed_amount=Decimal(2000), quantity=Decimal(1), percentage=None, percentage_base=None, formula_expression=None)
    result = _compute_rule_amount(rule, {"rules": {}, "categories": {}})
    assert result.amount == Decimal("2000.00")


def test_missing_contract_produces_blocker(db):
    employee = Employee(first_name="No", last_name="Contract", status=EmployeeStatus.ACTIVE)
    db.add(employee)
    db.commit()
    structure = _canonical_structure(db)
    payrun, payslip = _payslip_for(db, employee, structure)

    payroll_engine.compute_payslip(db, payslip)
    db.commit()

    assert payslip.net == Decimal(0)
    assert len(payslip.warnings) == 1
    assert payslip.warnings[0].code == "MISSING_CONTRACT"
    assert payslip.warnings[0].severity.value == "BLOCKER"


def test_unknown_dependency_produces_blocker_not_silent_zero(db):
    employee, contract = _setup_employee_with_contract(db)
    structure = SalaryStructure(name="Broken Structure", is_active=True)
    db.add(structure)
    db.flush()
    db.add(SalaryRule(salary_structure_id=structure.id, name="Bad HRA", code="HRA", category=RuleCategory.ALLOWANCE,
                       sequence=10, computation_method=ComputationMethod.PERCENTAGE, percentage=Decimal(20), percentage_base="BASCI"))
    db.commit()
    payrun, payslip = _payslip_for(db, employee, structure)

    payroll_engine.compute_payslip(db, payslip)
    db.commit()

    assert len(payslip.lines) == 0
    assert any(w.code == "RULE_FAILURE" and "BASCI" in w.message for w in payslip.warnings)
    assert payslip.allowances == Decimal(0)


def test_recompute_does_not_duplicate_lines(db):
    employee, contract = _setup_employee_with_contract(db)
    structure = _canonical_structure(db)
    payrun, payslip = _payslip_for(db, employee, structure)

    payroll_engine.compute_payslip(db, payslip)
    db.commit()
    first_count = len(payslip.lines)

    payroll_engine.compute_payslip(db, payslip)
    db.commit()
    assert len(payslip.lines) == first_count


def test_invalid_forward_reference_rejected(db):
    employee, contract = _setup_employee_with_contract(db)
    structure = SalaryStructure(name="Forward Ref Structure", is_active=True)
    db.add(structure)
    db.flush()
    # NET references GROSS, but GROSS is sequenced AFTER NET -> GROSS not yet in rules{}
    db.add_all([
        SalaryRule(salary_structure_id=structure.id, name="Net Salary", code="NET", category=RuleCategory.NET,
                   sequence=10, computation_method=ComputationMethod.FORMULA, formula_expression='rules["GROSS"]'),
        SalaryRule(salary_structure_id=structure.id, name="Gross Salary", code="GROSS", category=RuleCategory.GROSS,
                   sequence=20, computation_method=ComputationMethod.FIXED, fixed_amount=Decimal(10000)),
    ])
    db.commit()
    payrun, payslip = _payslip_for(db, employee, structure)

    payroll_engine.compute_payslip(db, payslip)
    db.commit()

    assert any(w.code == "RULE_FAILURE" and "GROSS" in w.message for w in payslip.warnings)
