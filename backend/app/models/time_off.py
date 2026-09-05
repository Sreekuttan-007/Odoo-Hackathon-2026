from sqlalchemy import Column, Integer, String, DateTime, Date, ForeignKey, Numeric, Text, Boolean, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base
import enum


class TimeOffUnit(str, enum.Enum):
    DAYS = "DAYS"
    HOURS = "HOURS"


class ApprovalPolicy(str, enum.Enum):
    NONE = "NONE"
    MANAGER = "MANAGER"
    HR = "HR"


class AllocationStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    TO_APPROVE = "TO_APPROVE"
    APPROVED = "APPROVED"
    REFUSED = "REFUSED"


class RequestStatus(str, enum.Enum):
    TO_APPROVE = "TO_APPROVE"
    APPROVED = "APPROVED"
    REFUSED = "REFUSED"


class TimeOffType(Base):
    __tablename__ = "time_off_types"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    code = Column(String, unique=True, index=True, nullable=True)
    unit = Column(Enum(TimeOffUnit), nullable=False, default=TimeOffUnit.DAYS)
    requires_allocation = Column(Boolean, nullable=False, default=True)
    approval_policy = Column(Enum(ApprovalPolicy), nullable=False, default=ApprovalPolicy.MANAGER)
    is_active = Column(Boolean, nullable=False, default=True)
    display_color = Column(String, nullable=True)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class TimeOffAllocation(Base):
    __tablename__ = "time_off_allocations"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    time_off_type_id = Column(Integer, ForeignKey("time_off_types.id"), nullable=False, index=True)

    allocated_amount = Column(Numeric(6, 2), nullable=False)
    valid_from = Column(Date, nullable=False)
    valid_to = Column(Date, nullable=False)

    status = Column(Enum(AllocationStatus), nullable=False, default=AllocationStatus.TO_APPROVE)
    approver_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    description = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    employee = relationship("Employee", foreign_keys=[employee_id])
    time_off_type = relationship("TimeOffType", foreign_keys=[time_off_type_id])
    approver = relationship("User", foreign_keys=[approver_user_id])


class TimeOffRequest(Base):
    __tablename__ = "time_off_requests"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    time_off_type_id = Column(Integer, ForeignKey("time_off_types.id"), nullable=False, index=True)

    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    # Snapshot of the computed duration at creation time (see
    # app/services/time_off_rules.py) — never recomputed on read, so a later
    # Working Schedule change cannot retroactively alter a historical request.
    duration_amount = Column(Numeric(6, 2), nullable=False)

    status = Column(Enum(RequestStatus), nullable=False, default=RequestStatus.TO_APPROVE)
    reason = Column(Text, nullable=True)

    approver_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    refused_at = Column(DateTime(timezone=True), nullable=True)

    allocation_id = Column(Integer, ForeignKey("time_off_allocations.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    employee = relationship("Employee", foreign_keys=[employee_id])
    time_off_type = relationship("TimeOffType", foreign_keys=[time_off_type_id])
    approver = relationship("User", foreign_keys=[approver_user_id])
    allocation = relationship("TimeOffAllocation", foreign_keys=[allocation_id])
