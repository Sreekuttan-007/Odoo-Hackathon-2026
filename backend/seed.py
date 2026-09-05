from sqlalchemy.orm import Session
from app.db.database import SessionLocal, engine
from app.models.user import User, Role, AccountStatus
from app.models.employee import Employee
from app.core.security import get_password_hash
from app.db.base import Base

def seed_db():
    print("Seeding database...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # Create Employees
    emp_admin = Employee(first_name="Alice", last_name="Admin", work_email="admin@payloom.local", department="Management")
    emp_hr = Employee(first_name="Bob", last_name="HR", work_email="hr@payloom.local", department="Human Resources")
    emp_payroll = Employee(first_name="Charlie", last_name="Payroll", work_email="payroll@payloom.local", department="Finance")
    emp_staff = Employee(first_name="Dave", last_name="Staff", work_email="employee@payloom.local", department="Engineering")
    emp_unlinked = Employee(first_name="Eve", last_name="Unlinked", work_email="eve@payloom.local", department="Sales")

    db.add_all([emp_admin, emp_hr, emp_payroll, emp_staff, emp_unlinked])
    db.commit()

    # Create Users
    user_admin = User(employee_id=emp_admin.id, work_email=emp_admin.work_email, role=Role.ADMIN, hashed_password=get_password_hash("admin123"))
    user_hr = User(employee_id=emp_hr.id, work_email=emp_hr.work_email, role=Role.HR_MANAGER, hashed_password=get_password_hash("hr123"))
    user_payroll = User(employee_id=emp_payroll.id, work_email=emp_payroll.work_email, role=Role.HR_PAYROLL_MANAGER, hashed_password=get_password_hash("payroll123"))
    user_staff = User(employee_id=emp_staff.id, work_email=emp_staff.work_email, role=Role.EMPLOYEE, hashed_password=get_password_hash("employee123"))

    db.add_all([user_admin, user_hr, user_payroll, user_staff])
    db.commit()

    print("Seeding complete.")

if __name__ == "__main__":
    seed_db()
