from datetime import date, time
from sqlalchemy.orm import Session
from app.db.database import SessionLocal, engine
from app.models.user import User, Role, AccountStatus
from app.models.employee import Employee, EmployeeStatus
from app.models.department import Department
from app.models.job_position import JobPosition
from app.models.working_schedule import WorkingSchedule, WorkingScheduleLine, ScheduleStatus, DayOfWeek
from app.models.contract import Contract
from app.core.security import get_password_hash
from app.db.base import Base
from app.services import contract_rules


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
        department_id=dept_management.id, job_position_id=pos_director.id, working_schedule_id=schedule_40h.id,
        status=EmployeeStatus.ACTIVE,
    )
    emp_hr = Employee(
        employee_code="EMP0002", first_name="Bob", last_name="HR", work_email="hr@payloom.local",
        department_id=dept_hr.id, job_position_id=pos_hr_manager.id, working_schedule_id=schedule_40h.id,
        status=EmployeeStatus.ACTIVE,
    )
    emp_payroll = Employee(
        employee_code="EMP0003", first_name="Charlie", last_name="Payroll", work_email="payroll@payloom.local",
        department_id=dept_finance.id, job_position_id=pos_payroll_manager.id, working_schedule_id=schedule_40h.id,
        status=EmployeeStatus.ACTIVE,
    )
    emp_staff = Employee(
        employee_code="EMP0004", first_name="Dave", last_name="Staff", work_email="employee@payloom.local",
        department_id=dept_engineering.id, job_position_id=pos_engineer.id, working_schedule_id=schedule_40h.id,
        status=EmployeeStatus.ACTIVE,
    )
    emp_unlinked = Employee(
        employee_code="EMP0005", first_name="Eve", last_name="Unlinked", work_email="eve@payloom.local",
        department_id=dept_sales.id, job_position_id=pos_sales_exec.id, working_schedule_id=schedule_48h.id,
        status=EmployeeStatus.ACTIVE,
    )
    db.add_all([emp_admin, emp_hr, emp_payroll, emp_staff, emp_unlinked])
    db.flush()

    # Demo employee for the manual demo flow: reports to Dave, matches
    # docs/PHASE_LOG.md / the organizer walkthrough (Aarav Mehta, two contracts).
    emp_aarav = Employee(
        employee_code="EMP0006", first_name="Aarav", last_name="Mehta", work_email="aarav.mehta@payloom.local",
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

    print("Seeding complete.")


if __name__ == "__main__":
    seed_db()
