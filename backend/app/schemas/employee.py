from pydantic import BaseModel, model_validator
from typing import Optional
from datetime import datetime
from app.models.employee import EmployeeStatus
from app.schemas.department import DepartmentResponse
from app.schemas.job_position import JobPositionResponse
from app.schemas.working_schedule import WorkingScheduleSummary


class EmployeeMinimal(BaseModel):
    id: int
    first_name: str
    last_name: str
    work_email: Optional[str] = None

    class Config:
        from_attributes = True


class EmployeeBase(BaseModel):
    first_name: str
    last_name: str
    work_email: Optional[str] = None
    work_location: Optional[str] = None
    status: EmployeeStatus = EmployeeStatus.ACTIVE
    department_id: Optional[int] = None
    job_position_id: Optional[int] = None
    manager_id: Optional[int] = None
    working_schedule_id: Optional[int] = None


class EmployeeCreate(EmployeeBase):
    pass


class EmployeeUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    work_email: Optional[str] = None
    work_location: Optional[str] = None
    status: Optional[EmployeeStatus] = None
    department_id: Optional[int] = None
    job_position_id: Optional[int] = None
    manager_id: Optional[int] = None
    working_schedule_id: Optional[int] = None


class EmployeeResponse(EmployeeBase):
    id: int
    employee_code: Optional[str] = None
    department: Optional[DepartmentResponse] = None
    job_position: Optional[JobPositionResponse] = None
    manager: Optional[EmployeeMinimal] = None
    working_schedule: Optional[WorkingScheduleSummary] = None
    contracts_count: int = 0
    attendance_count: int = 0
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
