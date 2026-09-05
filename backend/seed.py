"""Idempotent demo/dev data seed.

Safe to run more than once against the same database: every row is
looked up by a stable business identifier (employee_code, work_email,
department/job-position name, salary-rule code, etc.) before creating
it, so re-running never produces duplicate departments, employees,
users, or salary rules. This matters for Phase 8.5 (Neon): the same
script can be used to (re-)populate a demo database without wiping it
first.

This does NOT create the schema — that's Alembic's job
(`alembic upgrade head`). Run this only after migrations are applied.

Usage:
    python seed.py
"""
from datetime import date, datetime, time, timedelta, timezone
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.user import User, Role
from app.models.employee import Employee, EmployeeStatus
from app.models.department import Department
from app.models.job_position import JobPosition
from app.models.working_schedule import WorkingSchedule, WorkingScheduleLine, ScheduleStatus, DayOfWeek
from app.models.contract import Contract
from app.models.attendance import Attendance
from app.models.time_off import (
    TimeOffType, TimeOffAllocation, TimeOffRequest,
    TimeOffUnit, ApprovalPolicy, AllocationStatus, RequestStatus,
)
from app.models.payroll import SalaryStructure, SalaryRule, RuleCategory, ComputationMethod, Payrun, Payslip
from app.core.security import get_password_hash
from app.services import contract_rules, attendance_rules, payroll_engine


def _get_or_create(db: Session, model, defaults: dict = None, **lookup):
    """Looks up `model` by `lookup` kwargs; creates it with `lookup` +
    `defaults` merged in if not found. Returns (instance, created)."""
    instance = db.query(model).filter_by(**lookup).first()
    if instance:
        return instance, False
    instance = model(**{**lookup, **(defaults or {})})
    db.add(instance)
    db.flush()
    return instance, True


def seed_db():
    print("Seeding database (idempotent)...")
    db: Session = SessionLocal()

    # --- Departments ---
    dept_management, _ = _get_or_create(db, Department, name="Management")
    dept_hr, _ = _get_or_create(db, Department, name="Human Resources")
    dept_finance, _ = _get_or_create(db, Department, name="Finance")
    dept_engineering, _ = _get_or_create(db, Department, name="Engineering")
    dept_sales, _ = _get_or_create(db, Department, name="Sales")
    db.commit()

    # --- Job Positions (level: lower = more senior; see the employee
    # manager-hierarchy rule in app/api/employees.py) ---
    pos_director, _ = _get_or_create(db, JobPosition, title="Managing Director", defaults={"level": 1})
    pos_payroll_manager, _ = _get_or_create(db, JobPosition, title="Payroll Manager", defaults={"level": 2})
    pos_hr_manager, _ = _get_or_create(db, JobPosition, title="HR Manager", defaults={"level": 3})
    pos_engineer, _ = _get_or_create(db, JobPosition, title="Software Engineer", defaults={"level": 4})
    pos_sales_exec, _ = _get_or_create(db, JobPosition, title="Sales Executive", defaults={"level": 4})
    # Levels are static hierarchy metadata, not user-editable business data —
    # keep them authoritative even if the row already existed (e.g. created
    # before this field existed, or before the seed set it).
    pos_director.level = 1
    pos_payroll_manager.level = 2
    pos_hr_manager.level = 3
    pos_engineer.level = 4
    pos_sales_exec.level = 4
    db.commit()

    # --- Working Schedules ---
    schedule_40h, created = _get_or_create(
        db, WorkingSchedule, name="40 Hours / Week",
        defaults={"company": "Payloom Inc.", "timezone": "Asia/Kolkata", "status": ScheduleStatus.ACTIVE},
    )
    if created:
        for day in [DayOfWeek.MONDAY, DayOfWeek.TUESDAY, DayOfWeek.WEDNESDAY, DayOfWeek.THURSDAY, DayOfWeek.FRIDAY]:
            db.add(WorkingScheduleLine(working_schedule_id=schedule_40h.id, day_of_week=day, start_time=time(9, 0), end_time=time(18, 0), break_minutes=60))

    schedule_48h, created = _get_or_create(
        db, WorkingSchedule, name="48 Hours / Week",
        defaults={"company": "Payloom Inc.", "timezone": "Asia/Kolkata", "status": ScheduleStatus.ACTIVE},
    )
    if created:
        for day in [DayOfWeek.MONDAY, DayOfWeek.TUESDAY, DayOfWeek.WEDNESDAY, DayOfWeek.THURSDAY, DayOfWeek.FRIDAY, DayOfWeek.SATURDAY]:
            db.add(WorkingScheduleLine(working_schedule_id=schedule_48h.id, day_of_week=day, start_time=time(9, 0), end_time=time(18, 0), break_minutes=60))
    db.commit()

    # --- Employees ---
    emp_admin, _ = _get_or_create(db, Employee, employee_code="EMP0001", defaults={
        "first_name": "Alice", "last_name": "Admin", "work_email": "admin@payloom.local",
        "work_location": "Bengaluru HQ", "department_id": dept_management.id,
        "job_position_id": pos_director.id, "working_schedule_id": schedule_40h.id, "status": EmployeeStatus.ACTIVE,
    })
    emp_hr, _ = _get_or_create(db, Employee, employee_code="EMP0002", defaults={
        "first_name": "Bob", "last_name": "HR", "work_email": "hr@payloom.local",
        "work_location": "Bengaluru HQ", "department_id": dept_hr.id,
        "job_position_id": pos_hr_manager.id, "working_schedule_id": schedule_40h.id,
        "manager_id": emp_admin.id, "status": EmployeeStatus.ACTIVE,
    })
    emp_payroll, _ = _get_or_create(db, Employee, employee_code="EMP0003", defaults={
        "first_name": "Charlie", "last_name": "Payroll", "work_email": "payroll@payloom.local",
        "work_location": "Bengaluru HQ", "department_id": dept_finance.id,
        "job_position_id": pos_payroll_manager.id, "working_schedule_id": schedule_40h.id,
        "manager_id": emp_admin.id, "status": EmployeeStatus.ACTIVE,
    })
    emp_staff, _ = _get_or_create(db, Employee, employee_code="EMP0004", defaults={
        "first_name": "Dave", "last_name": "Staff", "work_email": "employee@payloom.local",
        "work_location": "Bengaluru HQ", "department_id": dept_engineering.id,
        "job_position_id": pos_engineer.id, "working_schedule_id": schedule_40h.id,
        "manager_id": emp_admin.id, "status": EmployeeStatus.ACTIVE,
    })
    emp_unlinked, _ = _get_or_create(db, Employee, employee_code="EMP0005", defaults={
        "first_name": "Eve", "last_name": "Unlinked", "work_email": "eve@payloom.local",
        "work_location": "Mumbai Office", "department_id": dept_sales.id,
        "job_position_id": pos_sales_exec.id, "working_schedule_id": schedule_48h.id,
        "manager_id": emp_admin.id, "status": EmployeeStatus.ACTIVE,
    })
    # Deliberately given NO Contract below — the "Preflight contract issue"
    # demo scenario (docs section 20): adding Eve to a new Payrun surfaces a
    # real MISSING_CONTRACT block, not a fabricated one.

    emp_aarav, _ = _get_or_create(db, Employee, employee_code="EMP0006", defaults={
        "first_name": "Aarav", "last_name": "Mehta", "work_email": "aarav.mehta@payloom.local",
        "work_location": "Bengaluru HQ", "department_id": dept_engineering.id,
        "job_position_id": pos_engineer.id, "working_schedule_id": schedule_40h.id,
        "manager_id": emp_staff.id, "status": EmployeeStatus.ACTIVE,
    })
    db.commit()

    # --- Contracts ---
    # Aarav: history of one expired + one running contract.
    _get_or_create(db, Contract, employee_id=emp_aarav.id, start_date=date(2025, 7, 1), defaults={
        "reference": contract_rules.generate_reference(db, date(2025, 7, 1)),
        "department_id": dept_engineering.id, "job_position_id": pos_engineer.id, "working_schedule_id": schedule_40h.id,
        "end_date": date(2025, 12, 31), "wage_monthly": 70000, "currency": "INR",
    })
    aarav_contract, _ = _get_or_create(db, Contract, employee_id=emp_aarav.id, start_date=date(2026, 1, 1), defaults={
        "reference": contract_rules.generate_reference(db, date(2026, 1, 1)),
        "department_id": dept_engineering.id, "job_position_id": pos_engineer.id, "working_schedule_id": schedule_40h.id,
        "end_date": None, "wage_monthly": 85000, "currency": "INR",
    })
    # Dave: a clean, single running contract — the second "clean payroll" demo subject.
    dave_contract, _ = _get_or_create(db, Contract, employee_id=emp_staff.id, start_date=date(2026, 1, 1), defaults={
        "reference": contract_rules.generate_reference(db, date(2026, 1, 1)),
        "department_id": dept_engineering.id, "job_position_id": pos_engineer.id, "working_schedule_id": schedule_40h.id,
        "end_date": None, "wage_monthly": 60000, "currency": "INR",
    })
    db.commit()

    # --- Users ---
    _get_or_create(db, User, work_email=emp_admin.work_email, defaults={"employee_id": emp_admin.id, "role": Role.ADMIN, "hashed_password": get_password_hash("admin123")})
    _get_or_create(db, User, work_email=emp_hr.work_email, defaults={"employee_id": emp_hr.id, "role": Role.HR_MANAGER, "hashed_password": get_password_hash("hr123")})
    _get_or_create(db, User, work_email=emp_payroll.work_email, defaults={"employee_id": emp_payroll.id, "role": Role.HR_PAYROLL_MANAGER, "hashed_password": get_password_hash("payroll123")})
    user_hr = db.query(User).filter_by(work_email=emp_hr.work_email).first()
    _get_or_create(db, User, work_email=emp_staff.work_email, defaults={"employee_id": emp_staff.id, "role": Role.EMPLOYEE, "hashed_password": get_password_hash("employee123")})
    db.commit()

    # --- Attendance ---
    company_tz = attendance_rules.COMPANY_TZ
    yesterday = attendance_rules.today_in_company_tz() - timedelta(days=1)

    def _at(day, hour, minute):
        return datetime(day.year, day.month, day.day, hour, minute, tzinfo=company_tz).astimezone(timezone.utc)

    _get_or_create(db, Attendance, employee_id=emp_staff.id, attendance_date=yesterday, defaults={
        "check_in": _at(yesterday, 9, 2), "check_out": _at(yesterday, 18, 5),
    })
    two_days_ago = attendance_rules.today_in_company_tz() - timedelta(days=2)
    three_days_ago = attendance_rules.today_in_company_tz() - timedelta(days=3)
    _get_or_create(db, Attendance, employee_id=emp_aarav.id, attendance_date=two_days_ago, defaults={
        "check_in": _at(two_days_ago, 9, 10), "check_out": _at(two_days_ago, 18, 0),
    })
    _get_or_create(db, Attendance, employee_id=emp_aarav.id, attendance_date=three_days_ago, defaults={
        "check_in": _at(three_days_ago, 9, 5), "check_out": None,
    })
    db.commit()

    # --- Time Off Types ---
    type_pto, _ = _get_or_create(db, TimeOffType, code="PTO", defaults={
        "name": "Paid Time Off", "unit": TimeOffUnit.DAYS, "requires_allocation": True,
        "approval_policy": ApprovalPolicy.MANAGER, "is_active": True, "display_color": "#4f46e5",
        "notes": "Annual paid leave balance, granted at the start of the policy year.",
    })
    type_sick, _ = _get_or_create(db, TimeOffType, code="SICK", defaults={
        "name": "Sick Leave", "unit": TimeOffUnit.DAYS, "requires_allocation": False,
        "approval_policy": ApprovalPolicy.MANAGER, "is_active": True, "display_color": "#dc2626",
        "notes": "No allocation required — self-certified, manager-approved.",
    })
    _get_or_create(db, TimeOffType, code="COMPOFF", defaults={
        "name": "Comp Off", "unit": TimeOffUnit.HOURS, "requires_allocation": True,
        "approval_policy": ApprovalPolicy.HR, "is_active": True, "display_color": "#0891b2",
        "notes": "Hourly compensatory leave granted for extra hours worked.",
    })
    db.commit()

    # --- Allocations ---
    aarav_pto_allocation, _ = _get_or_create(
        db, TimeOffAllocation, employee_id=emp_aarav.id, time_off_type_id=type_pto.id, valid_from=date(2026, 1, 1),
        defaults={
            "allocated_amount": 20, "valid_to": date(2026, 12, 31), "status": AllocationStatus.APPROVED,
            "approver_user_id": user_hr.id, "approved_at": attendance_rules.now_utc(), "description": "2026 Annual Balance",
        },
    )
    _get_or_create(
        db, TimeOffAllocation, employee_id=emp_staff.id, time_off_type_id=type_pto.id, valid_from=date(2026, 1, 1),
        defaults={
            "allocated_amount": 12, "valid_to": date(2026, 12, 31), "status": AllocationStatus.APPROVED,
            "approver_user_id": user_hr.id, "approved_at": attendance_rules.now_utc(), "description": "2026 Annual Balance",
        },
    )
    # A still-pending allocation, so the Approve/Refuse flow has a real
    # example to demo without touching the balances above.
    type_compoff = db.query(TimeOffType).filter_by(code="COMPOFF").first()
    _get_or_create(
        db, TimeOffAllocation, employee_id=emp_unlinked.id, time_off_type_id=type_compoff.id, valid_from=date(2026, 1, 1),
        defaults={
            "allocated_amount": 16, "valid_to": date(2026, 12, 31), "status": AllocationStatus.TO_APPROVE,
            "description": "Compensatory hours for Q3 project crunch.",
        },
    )
    db.commit()

    # --- Requests ---
    _get_or_create(
        db, TimeOffRequest, employee_id=emp_aarav.id, time_off_type_id=type_pto.id, start_date=date(2026, 1, 5),
        defaults={
            "end_date": date(2026, 1, 9), "duration_amount": 5, "status": RequestStatus.APPROVED,
            "approver_user_id": user_hr.id, "approved_at": attendance_rules.now_utc(),
            "allocation_id": aarav_pto_allocation.id, "reason": "Family trip.",
        },
    )
    demo_date = attendance_rules.today_in_company_tz() + timedelta(days=14)
    while demo_date.weekday() >= 5:
        demo_date += timedelta(days=1)
    _get_or_create(
        db, TimeOffRequest, employee_id=emp_staff.id, time_off_type_id=type_sick.id, start_date=demo_date,
        defaults={"end_date": demo_date, "duration_amount": 1, "status": RequestStatus.TO_APPROVE, "reason": "Doctor's appointment."},
    )
    db.commit()

    # --- Salary Structures / Rules ---
    structure_regular, _ = _get_or_create(db, SalaryStructure, code="REGULAR", defaults={
        "name": "Regular Salary", "is_active": True,
        "description": "Standard structure: Basic + HRA + Standard Allowance, less Provident Fund.",
    })
    for rule_kwargs in [
        dict(code="BASIC", defaults=dict(name="Basic Salary", category=RuleCategory.BASIC, sequence=1, computation_method=ComputationMethod.PERCENTAGE, percentage=50, percentage_base="CONTRACT_WAGE")),
        dict(code="HRA", defaults=dict(name="House Rent Allowance", category=RuleCategory.ALLOWANCE, sequence=10, computation_method=ComputationMethod.PERCENTAGE, percentage=20, percentage_base="BASIC")),
        dict(code="ALLOWANCE", defaults=dict(name="Standard Allowance", category=RuleCategory.ALLOWANCE, sequence=20, computation_method=ComputationMethod.FIXED, fixed_amount=2000)),
        dict(code="GROSS", defaults=dict(name="Gross Salary", category=RuleCategory.GROSS, sequence=60, computation_method=ComputationMethod.FORMULA, formula_expression='rules["BASIC"] + rules["HRA"] + rules["ALLOWANCE"]')),
        dict(code="PF", defaults=dict(name="Provident Fund", category=RuleCategory.DEDUCTION, sequence=80, computation_method=ComputationMethod.PERCENTAGE, percentage=10, percentage_base="BASIC")),
        dict(code="NET", defaults=dict(name="Net Salary", category=RuleCategory.NET, sequence=100, computation_method=ComputationMethod.FORMULA, formula_expression='rules["GROSS"] - rules["PF"]')),
    ]:
        _get_or_create(db, SalaryRule, salary_structure_id=structure_regular.id, code=rule_kwargs["code"], defaults=rule_kwargs["defaults"])

    structure_intern, _ = _get_or_create(db, SalaryStructure, code="INTERN", defaults={
        "name": "Intern Salary", "is_active": True, "description": "Flat stipend, no allowances or deductions.",
    })
    for rule_kwargs in [
        dict(code="BASIC", defaults=dict(name="Basic Salary", category=RuleCategory.BASIC, sequence=1, computation_method=ComputationMethod.PERCENTAGE, percentage=100, percentage_base="CONTRACT_WAGE")),
        dict(code="GROSS", defaults=dict(name="Gross Salary", category=RuleCategory.GROSS, sequence=60, computation_method=ComputationMethod.FORMULA, formula_expression='rules["BASIC"]')),
        dict(code="NET", defaults=dict(name="Net Salary", category=RuleCategory.NET, sequence=100, computation_method=ComputationMethod.FORMULA, formula_expression='rules["GROSS"]')),
    ]:
        _get_or_create(db, SalaryRule, salary_structure_id=structure_intern.id, code=rule_kwargs["code"], defaults=rule_kwargs["defaults"])
    db.commit()

    # --- Demo Payrun (Regular Salary, Feb 2026, Aarav + Dave) ---
    # Left at COMPUTED rather than pre-validated/paid, so the demo can walk
    # through Preflight -> Validate -> Mark Paid live. Exercises PayTrace
    # (structured trace on real FIXED/PERCENTAGE/FORMULA rules) and Preflight
    # against real historical data, per Phase 8.5's demo-data requirements.
    demo_payrun = db.query(Payrun).filter_by(
        salary_structure_id=structure_regular.id, period_start=date(2026, 2, 1), period_end=date(2026, 2, 28),
    ).first()
    if not demo_payrun:
        demo_payrun = Payrun(
            reference=payroll_engine.generate_reference(db, date(2026, 2, 1)),
            salary_structure_id=structure_regular.id, period_start=date(2026, 2, 1), period_end=date(2026, 2, 28),
        )
        db.add(demo_payrun)
        db.flush()
        for emp, contract in [(emp_aarav, aarav_contract), (emp_staff, dave_contract)]:
            db.add(Payslip(
                payrun_id=demo_payrun.id, employee_id=emp.id, contract_id=contract.id,
                salary_structure_id=structure_regular.id, period_start=date(2026, 2, 1), period_end=date(2026, 2, 28),
            ))
        db.commit()
        db.refresh(demo_payrun)
        payroll_engine.compute_payrun(db, demo_payrun)

    print("Seeding complete.")


if __name__ == "__main__":
    seed_db()
