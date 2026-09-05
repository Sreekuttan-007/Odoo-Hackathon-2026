from pydantic import BaseModel, model_validator
from typing import Optional
from datetime import datetime
from app.schemas.employee import EmployeeMinimal


class AttendanceUpdate(BaseModel):
    check_in: Optional[datetime] = None
    check_out: Optional[datetime] = None
    notes: Optional[str] = None

    @model_validator(mode="after")
    def validate_dates(self):
        if self.check_in is not None and self.check_out is not None and self.check_out < self.check_in:
            raise ValueError("check_out must be on or after check_in")
        return self


class AttendanceResponse(BaseModel):
    id: int
    employee: EmployeeMinimal
    attendance_date: str
    check_in: datetime
    check_out: Optional[datetime] = None
    worked_minutes: Optional[int] = None
    overtime_minutes: Optional[int] = None
    status: str
    notes: Optional[str] = None
    corrected_by_name: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CurrentAttendanceResponse(BaseModel):
    checked_in: bool
    attendance: Optional[AttendanceResponse] = None
