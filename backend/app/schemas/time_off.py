from pydantic import BaseModel, model_validator
from typing import Optional
from datetime import datetime, date
from decimal import Decimal
from app.models.time_off import TimeOffUnit, ApprovalPolicy, AllocationStatus, RequestStatus
from app.schemas.employee import EmployeeMinimal


class TimeOffTypeBase(BaseModel):
    name: str
    code: Optional[str] = None
    unit: TimeOffUnit = TimeOffUnit.DAYS
    requires_allocation: bool = True
    approval_policy: ApprovalPolicy = ApprovalPolicy.MANAGER
    is_active: bool = True
    display_color: Optional[str] = None
    notes: Optional[str] = None


class TimeOffTypeCreate(TimeOffTypeBase):
    pass


class TimeOffTypeUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    unit: Optional[TimeOffUnit] = None
    requires_allocation: Optional[bool] = None
    approval_policy: Optional[ApprovalPolicy] = None
    is_active: Optional[bool] = None
    display_color: Optional[str] = None
    notes: Optional[str] = None


class TimeOffTypeResponse(TimeOffTypeBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TimeOffTypeMinimal(BaseModel):
    id: int
    name: str
    unit: TimeOffUnit
    requires_allocation: bool
    is_active: bool

    class Config:
        from_attributes = True


class TimeOffAllocationCreate(BaseModel):
    employee_id: int
    time_off_type_id: int
    allocated_amount: Decimal
    valid_from: date
    valid_to: date
    description: Optional[str] = None

    @model_validator(mode="after")
    def validate_fields(self):
        if self.valid_to < self.valid_from:
            raise ValueError("valid_to must be on or after valid_from")
        if self.allocated_amount <= 0:
            raise ValueError("allocated_amount must be a positive amount")
        return self


class TimeOffAllocationUpdate(BaseModel):
    allocated_amount: Optional[Decimal] = None
    valid_from: Optional[date] = None
    valid_to: Optional[date] = None
    description: Optional[str] = None

    @model_validator(mode="after")
    def validate_fields(self):
        if self.allocated_amount is not None and self.allocated_amount <= 0:
            raise ValueError("allocated_amount must be a positive amount")
        if self.valid_from is not None and self.valid_to is not None and self.valid_to < self.valid_from:
            raise ValueError("valid_to must be on or after valid_from")
        return self


class TimeOffAllocationResponse(BaseModel):
    id: int
    employee: EmployeeMinimal
    time_off_type: TimeOffTypeMinimal
    allocated_amount: Decimal
    taken_amount: Decimal
    remaining_amount: Decimal
    valid_from: date
    valid_to: date
    status: AllocationStatus
    approver_name: Optional[str] = None
    approved_at: Optional[datetime] = None
    description: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TimeOffRequestCreate(BaseModel):
    employee_id: Optional[int] = None
    time_off_type_id: int
    start_date: date
    end_date: date
    reason: Optional[str] = None

    @model_validator(mode="after")
    def validate_dates(self):
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


class TimeOffRequestUpdate(BaseModel):
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    reason: Optional[str] = None

    @model_validator(mode="after")
    def validate_dates(self):
        if self.start_date is not None and self.end_date is not None and self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


class AllocationBalanceSnapshot(BaseModel):
    allocation_id: int
    before: Decimal
    consumed: Decimal
    remaining: Decimal


class TimeOffRequestResponse(BaseModel):
    id: int
    employee: EmployeeMinimal
    time_off_type: TimeOffTypeMinimal
    start_date: date
    end_date: date
    duration_amount: Decimal
    status: RequestStatus
    reason: Optional[str] = None
    approver_name: Optional[str] = None
    approved_at: Optional[datetime] = None
    refused_at: Optional[datetime] = None
    allocation_id: Optional[int] = None
    balance: Optional[AllocationBalanceSnapshot] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TimeOffBalanceResponse(BaseModel):
    allocation_id: Optional[int] = None
    unit: TimeOffUnit
    allocated: Decimal
    taken: Decimal
    remaining: Decimal
