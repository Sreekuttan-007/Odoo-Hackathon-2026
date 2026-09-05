from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.database import get_db
from app.models.contract import Contract
from app.models.department import Department
from app.models.employee import Employee
from app.models.job_position import JobPosition
from app.models.user import User
from app.models.working_schedule import WorkingSchedule
from app.schemas.contract import ContractResponse
from app.schemas.department import DepartmentResponse
from app.schemas.employee import EmployeeResponse
from app.schemas.job_position import JobPositionResponse
from app.schemas.working_schedule import WorkingScheduleResponse, WorkingScheduleSummary

router = APIRouter()


@router.get("/departments", response_model=List[DepartmentResponse])
def list_departments(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return db.query(Department).order_by(Department.name).all()


@router.get("/job-positions", response_model=List[JobPositionResponse])
def list_job_positions(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return db.query(JobPosition).order_by(JobPosition.title).all()


@router.get("/working-schedules", response_model=List[WorkingScheduleSummary])
def list_working_schedules(
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = db.query(WorkingSchedule)
    if search:
        query = query.filter(WorkingSchedule.name.ilike(f"%{search}%"))
    schedules = query.order_by(WorkingSchedule.name).all()
    return [
        WorkingScheduleSummary(
            id=schedule.id,
            name=schedule.name,
            company=schedule.company,
            status=schedule.status,
            days_per_week=len(schedule.lines),
            hours_per_week=sum(
                max(
                    0,
                    (line.end_time.hour * 60 + line.end_time.minute)
                    - (line.start_time.hour * 60 + line.start_time.minute)
                    - line.break_minutes,
                )
                for line in schedule.lines
            )
            / 60,
        )
        for schedule in schedules
    ]


@router.get("/working-schedules/{schedule_id}", response_model=WorkingScheduleResponse)
def get_working_schedule(
    schedule_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    schedule = db.query(WorkingSchedule).filter(WorkingSchedule.id == schedule_id).first()
    if not schedule:
        return None
    hours_per_week = sum(
        max(
            0,
            (line.end_time.hour * 60 + line.end_time.minute)
            - (line.start_time.hour * 60 + line.start_time.minute)
            - line.break_minutes,
        )
        for line in schedule.lines
    ) / 60
    return {
        **{column.name: getattr(schedule, column.name) for column in WorkingSchedule.__table__.columns},
        "lines": [
            {
                **{column.name: getattr(line, column.name) for column in line.__table__.columns},
                "derived_hours": max(
                    0,
                    (line.end_time.hour * 60 + line.end_time.minute)
                    - (line.start_time.hour * 60 + line.start_time.minute)
                    - line.break_minutes,
                ) / 60,
            }
            for line in schedule.lines
        ],
        "days_per_week": len(schedule.lines),
        "hours_per_week": hours_per_week,
    }


@router.get("/employees", response_model=List[EmployeeResponse])
def list_employees(
    search: Optional[str] = None,
    department_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = db.query(Employee)
    if search:
        term = f"%{search}%"
        query = query.filter(
            or_(
                Employee.first_name.ilike(term),
                Employee.last_name.ilike(term),
                Employee.work_email.ilike(term),
                Employee.employee_code.ilike(term),
            )
        )
    if department_id is not None:
        query = query.filter(Employee.department_id == department_id)
    if status:
        query = query.filter(Employee.status == status)
    return query.order_by(Employee.last_name, Employee.first_name).limit(limit).all()


@router.get("/employees/{employee_id}", response_model=EmployeeResponse)
def get_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return db.query(Employee).filter(Employee.id == employee_id).first()


@router.get("/contracts", response_model=List[ContractResponse])
def list_contracts(
    employee_id: Optional[int] = None,
    search: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = db.query(Contract)
    if employee_id is not None:
        query = query.filter(Contract.employee_id == employee_id)
    if search:
        query = query.filter(Contract.reference.ilike(f"%{search}%"))
    if status == "ACTIVE":
        query = query.filter(Contract.end_date.is_(None))
    elif status == "EXPIRED":
        query = query.filter(Contract.end_date.is_not(None))
    return query.order_by(Contract.start_date.desc()).all()


@router.get("/contracts/{contract_id}", response_model=ContractResponse)
def get_contract(
    contract_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return db.query(Contract).filter(Contract.id == contract_id).first()
