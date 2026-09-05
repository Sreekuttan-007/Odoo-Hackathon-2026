from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from typing import List, Optional
from app.db.database import get_db
from app.models.employee import Employee, EmployeeStatus
from app.models.department import Department
from app.models.job_position import JobPosition
from app.models.working_schedule import WorkingSchedule
from app.models.contract import Contract
from app.models.attendance import Attendance
from app.models.time_off import TimeOffRequest
from app.models.user import User
from app.schemas.employee import EmployeeResponse, EmployeeCreate, EmployeeUpdate, EmployeeMinimal
from app.schemas.department import DepartmentResponse
from app.schemas.job_position import JobPositionResponse
from app.api.deps import get_current_user, get_current_hr
from app.services.schedule_calculator import build_schedule_summary

router = APIRouter()


def _next_employee_code(db: Session) -> str:
    count = db.query(Employee).count()
    sequence = count + 1
    code = f"EMP{sequence:04d}"
    while db.query(Employee).filter(Employee.employee_code == code).first() is not None:
        sequence += 1
        code = f"EMP{sequence:04d}"
    return code


def _validate_relations(
    db: Session,
    department_id: Optional[int],
    job_position_id: Optional[int],
    working_schedule_id: Optional[int],
    manager_id: Optional[int],
    self_id: Optional[int],
) -> None:
    if department_id is not None and not db.query(Department).filter(Department.id == department_id).first():
        raise HTTPException(400, detail={"error": {"code": "NOT_FOUND", "message": "Department not found."}})
    if job_position_id is not None and not db.query(JobPosition).filter(JobPosition.id == job_position_id).first():
        raise HTTPException(400, detail={"error": {"code": "NOT_FOUND", "message": "Job position not found."}})
    if working_schedule_id is not None and not db.query(WorkingSchedule).filter(WorkingSchedule.id == working_schedule_id).first():
        raise HTTPException(400, detail={"error": {"code": "NOT_FOUND", "message": "Working schedule not found."}})
    if manager_id is not None:
        if self_id is not None and manager_id == self_id:
            raise HTTPException(400, detail={"error": {"code": "INVALID_MANAGER", "message": "An employee cannot be their own manager."}})
        if not db.query(Employee).filter(Employee.id == manager_id).first():
            raise HTTPException(400, detail={"error": {"code": "NOT_FOUND", "message": "Manager not found."}})


def _build_response(employee: Employee, contracts_count: int, attendance_count: int = 0, time_off_requests_count: int = 0) -> EmployeeResponse:
    return EmployeeResponse(
        id=employee.id,
        employee_code=employee.employee_code,
        first_name=employee.first_name,
        last_name=employee.last_name,
        work_email=employee.work_email,
        work_location=employee.work_location,
        status=employee.status,
        department_id=employee.department_id,
        job_position_id=employee.job_position_id,
        manager_id=employee.manager_id,
        working_schedule_id=employee.working_schedule_id,
        department=DepartmentResponse.model_validate(employee.department) if employee.department else None,
        job_position=JobPositionResponse.model_validate(employee.job_position) if employee.job_position else None,
        manager=EmployeeMinimal.model_validate(employee.manager) if employee.manager else None,
        working_schedule=build_schedule_summary(employee.working_schedule),
        contracts_count=contracts_count,
        attendance_count=attendance_count,
        time_off_requests_count=time_off_requests_count,
        created_at=employee.created_at,
        updated_at=employee.updated_at,
    )


def _to_response(db: Session, employee: Employee) -> EmployeeResponse:
    contracts_count = db.query(Contract).filter(Contract.employee_id == employee.id).count()
    attendance_count = db.query(Attendance).filter(Attendance.employee_id == employee.id).count()
    time_off_requests_count = db.query(TimeOffRequest).filter(TimeOffRequest.employee_id == employee.id).count()
    return _build_response(employee, contracts_count, attendance_count, time_off_requests_count)


@router.get("/employees", response_model=List[EmployeeResponse])
def list_employees(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    search: Optional[str] = None,
    department_id: Optional[int] = None,
    job_position_id: Optional[int] = None,
    status: Optional[EmployeeStatus] = None,
    skip: int = 0,
    limit: int = 200,
):
    query = db.query(Employee)

    if search:
        term = f"%{search}%"
        query = query.outerjoin(JobPosition, Employee.job_position_id == JobPosition.id).filter(
            or_(
                Employee.first_name.ilike(term),
                Employee.last_name.ilike(term),
                Employee.work_email.ilike(term),
                Employee.employee_code.ilike(term),
                JobPosition.title.ilike(term),
            )
        )
    if department_id is not None:
        query = query.filter(Employee.department_id == department_id)
    if job_position_id is not None:
        query = query.filter(Employee.job_position_id == job_position_id)
    if status is not None:
        query = query.filter(Employee.status == status)

    employees = query.order_by(Employee.first_name, Employee.last_name).offset(skip).limit(limit).all()

    contract_counts = dict(
        db.query(Contract.employee_id, func.count(Contract.id)).group_by(Contract.employee_id).all()
    )
    attendance_counts = dict(
        db.query(Attendance.employee_id, func.count(Attendance.id)).group_by(Attendance.employee_id).all()
    )
    time_off_counts = dict(
        db.query(TimeOffRequest.employee_id, func.count(TimeOffRequest.id)).group_by(TimeOffRequest.employee_id).all()
    )
    return [
        _build_response(
            employee,
            contract_counts.get(employee.id, 0),
            attendance_counts.get(employee.id, 0),
            time_off_counts.get(employee.id, 0),
        )
        for employee in employees
    ]


@router.get("/employees/{employee_id}", response_model=EmployeeResponse)
def get_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(404, detail={"error": {"code": "NOT_FOUND", "message": "Employee not found."}})
    return _to_response(db, employee)


@router.post("/employees", response_model=EmployeeResponse)
def create_employee(
    payload: EmployeeCreate,
    db: Session = Depends(get_db),
    current_hr: User = Depends(get_current_hr),
):
    _validate_relations(
        db, payload.department_id, payload.job_position_id, payload.working_schedule_id, payload.manager_id, self_id=None
    )

    employee = Employee(
        employee_code=_next_employee_code(db),
        first_name=payload.first_name,
        last_name=payload.last_name,
        work_email=payload.work_email,
        work_location=payload.work_location,
        status=payload.status,
        department_id=payload.department_id,
        job_position_id=payload.job_position_id,
        manager_id=payload.manager_id,
        working_schedule_id=payload.working_schedule_id,
    )
    db.add(employee)
    db.commit()
    db.refresh(employee)
    return _to_response(db, employee)


@router.patch("/employees/{employee_id}", response_model=EmployeeResponse)
def update_employee(
    employee_id: int,
    payload: EmployeeUpdate,
    db: Session = Depends(get_db),
    current_hr: User = Depends(get_current_hr),
):
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(404, detail={"error": {"code": "NOT_FOUND", "message": "Employee not found."}})

    data = payload.model_dump(exclude_unset=True)
    _validate_relations(
        db,
        data.get("department_id") if "department_id" in data else None,
        data.get("job_position_id") if "job_position_id" in data else None,
        data.get("working_schedule_id") if "working_schedule_id" in data else None,
        data.get("manager_id") if "manager_id" in data else None,
        self_id=employee.id,
    )

    for field, value in data.items():
        setattr(employee, field, value)

    db.commit()
    db.refresh(employee)
    return _to_response(db, employee)
