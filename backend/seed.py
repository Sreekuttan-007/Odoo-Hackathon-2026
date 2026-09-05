from datetime import date, datetime, time, timedelta, timezone
from sqlalchemy.orm import Session
from app.db.database import SessionLocal, engine
from app.models.user import User, Role, AccountStatus
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
from app.core.security import get_password_hash
from app.db.base import Base
from app.services import contract_rules, attendance_rules, time_off_rules


def seed_db():
    print("Seeding database...")
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()

    # --- Departments ---
    dept_management = Department(name="Management")
    dept_hr = Department(name="Human Resources")
    dept_finance = Department(name="Finance")
    dept_engineering = Department(name="Engineering")
    dept_sales = Department(name="Sales")
    db.add_all([dept_management, dept_hr, dept_finance, dept_engineering, dept_sales])
    db.commit()

    # --- Job Positions ---
    pos_director = JobPosition(title="Managing Director")
    pos_hr_manager = JobPosition(title="HR Manager")
    pos_payroll_manager = JobPosition(title="Payroll Manager")
    pos_engineer = JobPosition(title="Software Engineer")
    pos_sales_exec = JobPosition(title="Sales Executive")
    db.add_all([pos_director, pos_hr_manager, pos_payroll_manager, pos_engineer, pos_sales_exec])
    db.commit()

    # --- Working Schedules ---
    schedule_40h = WorkingSchedule(name="40 Hours / Week", company="Payloom Inc.", timezone="Asia/Kolkata", status=ScheduleStatus.ACTIVE)
    db.add(schedule_40h)
    db.flush()
    for day in [DayOfWeek.MONDAY, DayOfWeek.TUESDAY, DayOfWeek.WEDNESDAY, DayOfWeek.THURSDAY, DayOfWeek.FRIDAY]:
        db.add(WorkingScheduleLine(
            working_schedule_id=schedule_40h.id,
            day_of_week=day,
            start_time=time(9, 0),
            end_time=time(18, 0),
            break_minutes=60,
        ))

    schedule_48h = WorkingSchedule(name="48 Hours / Week", company="Payloom Inc.", timezone="Asia/Kolkata", status=ScheduleStatus.ACTIVE)
    db.add(schedule_48h)
    db.flush()
    for day in [DayOfWeek.MONDAY, DayOfWeek.TUESDAY, DayOfWeek.WEDNESDAY, DayOfWeek.THURSDAY, DayOfWeek.FRIDAY, DayOfWeek.SATURDAY]:
        db.add(WorkingScheduleLine(
            working_schedule_id=schedule_48h.id,
            day_of_week=day,
            start_time=time(9, 0),
            end_time=time(18, 0),
            break_minutes=60,
        ))
    db.commit()

    # --- Employees ---
    emp_admin = Employee(
        employee_code="EMP0001", first_name="Alice", last_name="Admin", work_email="admin@payloom.local",
        work_location="Bengaluru HQ",
        department_id=dept_management.id, job_position_id=pos_director.id, working_schedule_id=schedule_40h.id,
        status=EmployeeStatus.ACTIVE,
    )
    db.add(emp_admin)
    db.flush()

    emp_hr = Employee(
        employee_code="EMP0002", first_name="Bob", last_name="HR", work_email="hr@payloom.local",
        work_location="Bengaluru HQ",
        department_id=dept_hr.id, job_position_id=pos_hr_manager.id, working_schedule_id=schedule_40h.id,
        manager_id=emp_admin.id, status=EmployeeStatus.ACTIVE,
    )
    emp_payroll = Employee(
        employee_code="EMP0003", first_name="Charlie", last_name="Payroll", work_email="payroll@payloom.local",
        work_location="Bengaluru HQ",
        department_id=dept_finance.id, job_position_id=pos_payroll_manager.id, working_schedule_id=schedule_40h.id,
        manager_id=emp_admin.id, status=EmployeeStatus.ACTIVE,
    )
    emp_staff = Employee(
        employee_code="EMP0004", first_name="Dave", last_name="Staff", work_email="employee@payloom.local",
        work_location="Bengaluru HQ",
        department_id=dept_engineering.id, job_position_id=pos_engineer.id, working_schedule_id=schedule_40h.id,
        manager_id=emp_admin.id, status=EmployeeStatus.ACTIVE,
    )
    emp_unlinked = Employee(
        employee_code="EMP0005", first_name="Eve", last_name="Unlinked", work_email="eve@payloom.local",
        work_location="Mumbai Office",
        department_id=dept_sales.id, job_position_id=pos_sales_exec.id, working_schedule_id=schedule_48h.id,
        manager_id=emp_admin.id, status=EmployeeStatus.ACTIVE,
    )
    db.add_all([emp_hr, emp_payroll, emp_staff, emp_unlinked])
    db.flush()

    # Demo employee for the manual demo flow: reports to Dave, matches
    # docs/PHASE_LOG.md / the organizer walkthrough (Aarav Mehta, two contracts).
    emp_aarav = Employee(
        employee_code="EMP0006", first_name="Aarav", last_name="Mehta", work_email="aarav.mehta@payloom.local",
        work_location="Bengaluru HQ",
        department_id=dept_engineering.id, job_position_id=pos_engineer.id, working_schedule_id=schedule_40h.id,
        manager_id=emp_staff.id, status=EmployeeStatus.ACTIVE,
    )
    db.add(emp_aarav)
    db.flush()

    # --- Contracts (Aarav's history: one expired, one running) ---
    expired_contract = Contract(
        reference=contract_rules.generate_reference(db, date(2025, 7, 1)),
        employee_id=emp_aarav.id, department_id=dept_engineering.id, job_position_id=pos_engineer.id,
        working_schedule_id=schedule_40h.id,
        start_date=date(2025, 7, 1), end_date=date(2025, 12, 31),
        wage_monthly=70000, currency="INR",
    )
    db.add(expired_contract)
    db.flush()

    running_contract = Contract(
        reference=contract_rules.generate_reference(db, date(2026, 1, 1)),
        employee_id=emp_aarav.id, department_id=dept_engineering.id, job_position_id=pos_engineer.id,
        working_schedule_id=schedule_40h.id,
        start_date=date(2026, 1, 1), end_date=None,
        wage_monthly=85000, currency="INR",
    )
    db.add(running_contract)
    db.commit()

    # --- Users ---
    user_admin = User(employee_id=emp_admin.id, work_email=emp_admin.work_email, role=Role.ADMIN, hashed_password=get_password_hash("admin123"))
    user_hr = User(employee_id=emp_hr.id, work_email=emp_hr.work_email, role=Role.HR_MANAGER, hashed_password=get_password_hash("hr123"))
    user_payroll = User(employee_id=emp_payroll.id, work_email=emp_payroll.work_email, role=Role.HR_PAYROLL_MANAGER, hashed_password=get_password_hash("payroll123"))
    user_staff = User(employee_id=emp_staff.id, work_email=emp_staff.work_email, role=Role.EMPLOYEE, hashed_password=get_password_hash("employee123"))

    db.add_all([user_admin, user_hr, user_payroll, user_staff])
    db.commit()

    # --- Attendance ---
    # Dave (the EMPLOYEE-role demo login) has a clean, completed record from
    # yesterday and NO open session, so the manual demo's live Check In /
    # Check Out flow (docs/PHASE_LOG.md Phase 3) works immediately.
    company_tz = attendance_rules.COMPANY_TZ
    yesterday = attendance_rules.today_in_company_tz() - timedelta(days=1)

    def _at(day, hour, minute):
        return datetime(day.year, day.month, day.day, hour, minute, tzinfo=company_tz).astimezone(timezone.utc)

    dave_yesterday = Attendance(
        employee_id=emp_staff.id, attendance_date=yesterday,
        check_in=_at(yesterday, 9, 2), check_out=_at(yesterday, 18, 5),
    )

    # Aarav has a normal completed day two days ago, plus an OPEN session
    # from three days ago that was never checked out — the deliberate
    # "Missing Checkout" example HR corrects during the failure demo
    # (docs/PHASE_LOG.md Phase 3, section 41). Aarav has no login, so this
    # open session never blocks anyone's live check-in.
    two_days_ago = attendance_rules.today_in_company_tz() - timedelta(days=2)
    three_days_ago = attendance_rules.today_in_company_tz() - timedelta(days=3)
    aarav_completed = Attendance(
        employee_id=emp_aarav.id, attendance_date=two_days_ago,
        check_in=_at(two_days_ago, 9, 10), check_out=_at(two_days_ago, 18, 0),
    )
    aarav_missing_checkout = Attendance(
        employee_id=emp_aarav.id, attendance_date=three_days_ago,
        check_in=_at(three_days_ago, 9, 5), check_out=None,
    )

    db.add_all([dave_yesterday, aarav_completed, aarav_missing_checkout])
    db.commit()

    # --- Time Off Types ---
    type_pto = TimeOffType(
        name="Paid Time Off", code="PTO", unit=TimeOffUnit.DAYS,
        requires_allocation=True, approval_policy=ApprovalPolicy.MANAGER,
        is_active=True, display_color="#4f46e5",
        notes="Annual paid leave balance, granted at the start of the policy year.",
    )
    type_sick = TimeOffType(
        name="Sick Leave", code="SICK", unit=TimeOffUnit.DAYS,
        requires_allocation=False, approval_policy=ApprovalPolicy.MANAGER,
        is_active=True, display_color="#dc2626",
        notes="No allocation required — self-certified, manager-approved.",
    )
    type_compoff = TimeOffType(
        name="Comp Off", code="COMPOFF", unit=TimeOffUnit.HOURS,
        requires_allocation=True, approval_policy=ApprovalPolicy.HR,
        is_active=True, display_color="#0891b2",
        notes="Hourly compensatory leave granted for extra hours worked.",
    )
    db.add_all([type_pto, type_sick, type_compoff])
    db.commit()

    # --- Allocations ---
    # Aarav: the organizer-example numbers (docs/PHASE_LOG.md manual demo) —
    # 20 allocated, 5 already taken (see the APPROVED request below), 15
    # remaining. This is also the exact balance-math test case from the
    # Phase 4 spec (section 73): a further 3-day approval should land at
    # taken=8 / remaining=12.
    aarav_pto_allocation = TimeOffAllocation(
        employee_id=emp_aarav.id, time_off_type_id=type_pto.id,
        allocated_amount=20, valid_from=date(2026, 1, 1), valid_to=date(2026, 12, 31),
        status=AllocationStatus.APPROVED, approver_user_id=user_hr.id, approved_at=attendance_rules.now_utc(),
        description="2026 Annual Balance",
    )
    # Dave (the EMPLOYEE-role demo login) gets a fresh, untouched allocation
    # so the live self-service "create a request" demo has real balance to
    # consume, independent of Aarav's history.
    dave_pto_allocation = TimeOffAllocation(
        employee_id=emp_staff.id, time_off_type_id=type_pto.id,
        allocated_amount=12, valid_from=date(2026, 1, 1), valid_to=date(2026, 12, 31),
        status=AllocationStatus.APPROVED, approver_user_id=user_hr.id, approved_at=attendance_rules.now_utc(),
        description="2026 Annual Balance",
    )
    db.add_all([aarav_pto_allocation, dave_pto_allocation])
    db.flush()

    # A still-pending allocation, so the Allocations list/detail Approve/Refuse
    # flow has a real example to demo without touching the balances above.
    eve_compoff_allocation = TimeOffAllocation(
        employee_id=emp_unlinked.id, time_off_type_id=type_compoff.id,
        allocated_amount=16, valid_from=date(2026, 1, 1), valid_to=date(2026, 12, 31),
        status=AllocationStatus.TO_APPROVE,
        description="Compensatory hours for Q3 project crunch.",
    )
    db.add(eve_compoff_allocation)
    db.commit()

    # --- Requests ---
    # Aarav's already-consumed 5 working days (Mon 5 Jan – Fri 9 Jan 2026,
    # against his 40 Hours/Week schedule) — pre-approved history.
    aarav_pto_request = TimeOffRequest(
        employee_id=emp_aarav.id, time_off_type_id=type_pto.id,
        start_date=date(2026, 1, 5), end_date=date(2026, 1, 9), duration_amount=5,
        status=RequestStatus.APPROVED, approver_user_id=user_hr.id, approved_at=attendance_rules.now_utc(),
        allocation_id=aarav_pto_allocation.id, reason="Family trip.",
    )

    # A pending request for Dave, dated a couple of weeks out on the next
    # working day — a live example for the Approve/Refuse demo that needs
    # no allocation (Sick Leave doesn't require one).
    demo_date = attendance_rules.today_in_company_tz() + timedelta(days=14)
    while demo_date.weekday() >= 5:
        demo_date += timedelta(days=1)
    dave_sick_request = TimeOffRequest(
        employee_id=emp_staff.id, time_off_type_id=type_sick.id,
        start_date=demo_date, end_date=demo_date, duration_amount=1,
        status=RequestStatus.TO_APPROVE, reason="Doctor's appointment.",
    )

    db.add_all([aarav_pto_request, dave_sick_request])
    db.commit()

    print("Seeding complete.")


if __name__ == "__main__":
    seed_db()
