from pydantic import BaseModel, model_validator
from typing import Optional
from datetime import datetime, date
from decimal import Decimal
from app.schemas.employee import EmployeeMinimal
from app.schemas.department import DepartmentResponse
from app.schemas.job_position import JobPositionResponse
from app.schemas.working_schedule import WorkingScheduleSummary


class ContractBase(BaseModel):
    department_id: int
    job_position_id: int
    working_schedule_id: Optional[int] = None
    start_date: date
    end_date: Optional[date] = None
    wage_monthly: Decimal
    currency: str = "INR"
    salary_structure_note: Optional[str] = None

    @model_validator(mode="after")
    def validate_dates_and_wage(self):
        if self.end_date is not None and self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        if self.wage_monthly <= 0:
            raise ValueError("wage_monthly must be a positive amount")
        return self


class ContractCreate(ContractBase):
    employee_id: int


class ContractUpdate(BaseModel):
    department_id: Optional[int] = None
    job_position_id: Optional[int] = None
    working_schedule_id: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    wage_monthly: Optional[Decimal] = None
    currency: Optional[str] = None
    salary_structure_note: Optional[str] = None

    @model_validator(mode="after")
    def validate_wage(self):
        if self.wage_monthly is not None and self.wage_monthly <= 0:
            raise ValueError("wage_monthly must be a positive amount")
        if (
            self.start_date is not None
            and self.end_date is not None
            and self.end_date < self.start_date
        ):
            raise ValueError("end_date must be on or after start_date")
        return self


class ContractResponse(ContractBase):
    id: int
    reference: str
    status: str
    employee: EmployeeMinimal
    department: DepartmentResponse
    job_position: JobPositionResponse
    working_schedule: Optional[WorkingScheduleSummary] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
