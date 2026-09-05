from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional
from datetime import date
from decimal import Decimal
from app.db.database import get_db
from app.models.employee import Employee
from app.models.user import User
from app.models.time_off import (
    TimeOffType, TimeOffAllocation, TimeOffRequest,
    AllocationStatus, RequestStatus,
)
from app.schemas.employee import EmployeeMinimal
from app.schemas.time_off import (
    TimeOffTypeResponse, TimeOffTypeCreate, TimeOffTypeUpdate, TimeOffTypeMinimal,
    TimeOffAllocationResponse, TimeOffAllocationCreate, TimeOffAllocationUpdate,
    TimeOffRequestResponse, TimeOffRequestCreate, TimeOffRequestUpdate,
    TimeOffBalanceResponse, AllocationBalanceSnapshot,
)
from app.api.deps import get_current_user, get_current_hr, HR_CAPABLE_ROLES
from app.services import time_off_rules as rules

router = APIRouter()


# ---------------------------------------------------------------- Types ----

@router.get("/time-off/types", response_model=List[TimeOffTypeResponse])
def list_types(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    unit: Optional[str] = None,
):
    query = db.query(TimeOffType)
    if search:
        query = query.filter(TimeOffType.name.ilike(f"%{search}%"))
    if is_active is not None:
        query = query.filter(TimeOffType.is_active == is_active)
    if unit:
        query = query.filter(TimeOffType.unit == unit.upper())
    return query.order_by(TimeOffType.name).all()


@router.post("/time-off/types", response_model=TimeOffTypeResponse)
def create_type(
    payload: TimeOffTypeCreate,
    db: Session = Depends(get_db),
    current_hr: User = Depends(get_current_hr),
):
    if payload.code and db.query(TimeOffType).filter(TimeOffType.code == payload.code).first():
        raise HTTPException(409, detail={"error": {"code": "DUPLICATE_CODE", "message": "A Time Off Type with this code already exists."}})
    time_off_type = TimeOffType(**payload.model_dump())
    db.add(time_off_type)
    db.commit()
    db.refresh(time_off_type)
    return time_off_type


@router.get("/time-off/types/{type_id}", response_model=TimeOffTypeResponse)
def get_type(type_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    time_off_type = db.query(TimeOffType).filter(TimeOffType.id == type_id).first()
    if not time_off_type:
        raise HTTPException(404, detail={"error": {"code": "NOT_FOUND", "message": "Time Off Type not found."}})
    return time_off_type


@router.patch("/time-off/types/{type_id}", response_model=TimeOffTypeResponse)
def update_type(
    type_id: int,
    payload: TimeOffTypeUpdate,
    db: Session = Depends(get_db),
    current_hr: User = Depends(get_current_hr),
):
    time_off_type = db.query(TimeOffType).filter(TimeOffType.id == type_id).first()
    if not time_off_type:
        raise HTTPException(404, detail={"error": {"code": "NOT_FOUND", "message": "Time Off Type not found."}})

    data = payload.model_dump(exclude_unset=True)
    if "code" in data and data["code"] and db.query(TimeOffType).filter(TimeOffType.code == data["code"], TimeOffType.id != type_id).first():
        raise HTTPException(409, detail={"error": {"code": "DUPLICATE_CODE", "message": "A Time Off Type with this code already exists."}})

    if "unit" in data and data["unit"] != time_off_type.unit:
        referenced = (
            db.query(TimeOffAllocation).filter(TimeOffAllocation.time_off_type_id == type_id).first()
            or db.query(TimeOffRequest).filter(TimeOffRequest.time_off_type_id == type_id).first()
        )
        if referenced:
            raise HTTPException(409, detail={"error": {"code": "UNIT_LOCKED", "message": str(rules.UnitLockedError())}})

    for field, value in data.items():
        setattr(time_off_type, field, value)
    db.commit()
    db.refresh(time_off_type)
    return time_off_type


# --------------------------------------------------------- Allocations ----

def _allocation_response(db: Session, allocation: TimeOffAllocation) -> TimeOffAllocationResponse:
    taken, remaining = rules.compute_balance(db, allocation)
    approver_name = None
    if allocation.approver and allocation.approver.employee:
        approver_name = f"{allocation.approver.employee.first_name} {allocation.approver.employee.last_name}"
    return TimeOffAllocationResponse(
        id=allocation.id,
        employee=EmployeeMinimal.model_validate(allocation.employee),
        time_off_type=TimeOffTypeMinimal.model_validate(allocation.time_off_type),
        allocated_amount=allocation.allocated_amount,
        taken_amount=taken,
        remaining_amount=remaining,
        valid_from=allocation.valid_from,
        valid_to=allocation.valid_to,
        status=allocation.status,
        approver_name=approver_name,
        approved_at=allocation.approved_at,
        description=allocation.description,
        created_at=allocation.created_at,
        updated_at=allocation.updated_at,
    )


@router.get("/time-off/allocations", response_model=List[TimeOffAllocationResponse])
def list_allocations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    employee_id: Optional[int] = None,
    time_off_type_id: Optional[int] = None,
    status: Optional[str] = None,
):
    query = db.query(TimeOffAllocation)
    if current_user.role not in HR_CAPABLE_ROLES:
        query = query.filter(TimeOffAllocation.employee_id == current_user.employee_id)
    elif employee_id is not None:
        query = query.filter(TimeOffAllocation.employee_id == employee_id)
    if time_off_type_id is not None:
        query = query.filter(TimeOffAllocation.time_off_type_id == time_off_type_id)
    if status:
        query = query.filter(TimeOffAllocation.status == status.upper())
    allocations = query.order_by(TimeOffAllocation.valid_from.desc()).all()
    return [_allocation_response(db, a) for a in allocations]


@router.post("/time-off/allocations", response_model=TimeOffAllocationResponse)
def create_allocation(
    payload: TimeOffAllocationCreate,
    db: Session = Depends(get_db),
    current_hr: User = Depends(get_current_hr),
):
    employee = db.query(Employee).filter(Employee.id == payload.employee_id).first()
    if not employee:
        raise HTTPException(400, detail={"error": {"code": "NOT_FOUND", "message": "Employee not found."}})
    time_off_type = db.query(TimeOffType).filter(TimeOffType.id == payload.time_off_type_id).first()
    if not time_off_type:
        raise HTTPException(400, detail={"error": {"code": "NOT_FOUND", "message": "Time Off Type not found."}})

    allocation = TimeOffAllocation(
        employee_id=payload.employee_id,
        time_off_type_id=payload.time_off_type_id,
        allocated_amount=payload.allocated_amount,
        valid_from=payload.valid_from,
        valid_to=payload.valid_to,
        description=payload.description,
        status=AllocationStatus.TO_APPROVE,
    )
    db.add(allocation)
    db.commit()
    db.refresh(allocation)
    return _allocation_response(db, allocation)


@router.get("/time-off/allocations/{allocation_id}", response_model=TimeOffAllocationResponse)
def get_allocation(allocation_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    allocation = db.query(TimeOffAllocation).filter(TimeOffAllocation.id == allocation_id).first()
    if not allocation:
        raise HTTPException(404, detail={"error": {"code": "NOT_FOUND", "message": "Allocation not found."}})
    if current_user.role not in HR_CAPABLE_ROLES and allocation.employee_id != current_user.employee_id:
        raise HTTPException(403, detail={"error": {"code": "ACCESS_DENIED", "message": "You don't have access to this allocation."}})
    return _allocation_response(db, allocation)


@router.patch("/time-off/allocations/{allocation_id}", response_model=TimeOffAllocationResponse)
def update_allocation(
    allocation_id: int,
    payload: TimeOffAllocationUpdate,
    db: Session = Depends(get_db),
    current_hr: User = Depends(get_current_hr),
):
    allocation = db.query(TimeOffAllocation).filter(TimeOffAllocation.id == allocation_id).first()
    if not allocation:
        raise HTTPException(404, detail={"error": {"code": "NOT_FOUND", "message": "Allocation not found."}})
    if allocation.status != AllocationStatus.TO_APPROVE:
        raise HTTPException(409, detail={"error": {"code": "ALREADY_DECIDED", "message": "Only a pending allocation can be edited; refuse and create a new one instead."}})

    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(allocation, field, value)
    db.commit()
    db.refresh(allocation)
    return _allocation_response(db, allocation)


@router.post("/time-off/allocations/{allocation_id}/approve", response_model=TimeOffAllocationResponse)
def approve_allocation(allocation_id: int, db: Session = Depends(get_db), current_hr: User = Depends(get_current_hr)):
    allocation = db.query(TimeOffAllocation).filter(TimeOffAllocation.id == allocation_id).first()
    if not allocation:
        raise HTTPException(404, detail={"error": {"code": "NOT_FOUND", "message": "Allocation not found."}})
    try:
        rules.approve_allocation(db, allocation, current_hr.id)
    except rules.AlreadyDecidedError as exc:
        raise HTTPException(409, detail={"error": {"code": "ALREADY_DECIDED", "message": str(exc)}})
    except rules.AllocationOverlapError as exc:
        raise HTTPException(409, detail={"error": {"code": "ALLOCATION_OVERLAP", "message": str(exc), "details": {"conflicting_allocation_id": exc.conflicting.id}}})
    return _allocation_response(db, allocation)


@router.post("/time-off/allocations/{allocation_id}/refuse", response_model=TimeOffAllocationResponse)
def refuse_allocation(allocation_id: int, db: Session = Depends(get_db), current_hr: User = Depends(get_current_hr)):
    allocation = db.query(TimeOffAllocation).filter(TimeOffAllocation.id == allocation_id).first()
    if not allocation:
        raise HTTPException(404, detail={"error": {"code": "NOT_FOUND", "message": "Allocation not found."}})
    try:
        rules.refuse_allocation(db, allocation, current_hr.id)
    except rules.AlreadyDecidedError as exc:
        raise HTTPException(409, detail={"error": {"code": "ALREADY_DECIDED", "message": str(exc)}})
    return _allocation_response(db, allocation)


# ------------------------------------------------------------- Requests ----

def _require_self_employee_id(current_user: User) -> int:
    if current_user.employee_id is None:
        raise HTTPException(400, detail={"error": {"code": "NO_EMPLOYEE_LINK", "message": "Your account isn't linked to an employee record."}})
    return current_user.employee_id


def _request_response(db: Session, request: TimeOffRequest, include_balance: bool = True) -> TimeOffRequestResponse:
    approver_name = None
    if request.approver and request.approver.employee:
        approver_name = f"{request.approver.employee.first_name} {request.approver.employee.last_name}"

    balance = None
    if include_balance and request.allocation_id is not None:
        allocation = request.allocation
        taken, remaining = rules.compute_balance(db, allocation)
        if request.status == RequestStatus.APPROVED:
            before = remaining + request.duration_amount
        else:
            before = remaining
        balance = AllocationBalanceSnapshot(
            allocation_id=allocation.id,
            before=before,
            consumed=request.duration_amount if request.status == RequestStatus.APPROVED else Decimal(0),
            remaining=remaining,
        )

    return TimeOffRequestResponse(
        id=request.id,
        employee=EmployeeMinimal.model_validate(request.employee),
        time_off_type=TimeOffTypeMinimal.model_validate(request.time_off_type),
        start_date=request.start_date,
        end_date=request.end_date,
        duration_amount=request.duration_amount,
        status=request.status,
        reason=request.reason,
        approver_name=approver_name,
        approved_at=request.approved_at,
        refused_at=request.refused_at,
        allocation_id=request.allocation_id,
        balance=balance,
        created_at=request.created_at,
        updated_at=request.updated_at,
    )


@router.get("/time-off/requests", response_model=List[TimeOffRequestResponse])
def list_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    employee_id: Optional[int] = None,
    time_off_type_id: Optional[int] = None,
    status: Optional[str] = None,
):
    query = db.query(TimeOffRequest)
    if current_user.role not in HR_CAPABLE_ROLES:
        query = query.filter(TimeOffRequest.employee_id == current_user.employee_id)
    elif employee_id is not None:
        query = query.filter(TimeOffRequest.employee_id == employee_id)
    if time_off_type_id is not None:
        query = query.filter(TimeOffRequest.time_off_type_id == time_off_type_id)
    if status:
        query = query.filter(TimeOffRequest.status == status.upper())
    requests = query.order_by(TimeOffRequest.start_date.desc()).all()
    return [_request_response(db, r) for r in requests]


def _resolve_request_employee(db: Session, current_user: User, requested_employee_id: Optional[int]) -> Employee:
    if current_user.role not in HR_CAPABLE_ROLES:
        employee_id = _require_self_employee_id(current_user)
        if requested_employee_id is not None and requested_employee_id != employee_id:
            raise HTTPException(403, detail={"error": {"code": "ACCESS_DENIED", "message": "You can only create time off requests for yourself."}})
    else:
        employee_id = requested_employee_id if requested_employee_id is not None else _require_self_employee_id(current_user)
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(400, detail={"error": {"code": "NOT_FOUND", "message": "Employee not found."}})
    return employee


@router.post("/time-off/requests", response_model=TimeOffRequestResponse)
def create_request(
    payload: TimeOffRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    employee = _resolve_request_employee(db, current_user, payload.employee_id)

    time_off_type = db.query(TimeOffType).filter(TimeOffType.id == payload.time_off_type_id).first()
    if not time_off_type:
        raise HTTPException(400, detail={"error": {"code": "NOT_FOUND", "message": "Time Off Type not found."}})
    if not time_off_type.is_active:
        raise HTTPException(400, detail={"error": {"code": "TYPE_INACTIVE", "message": str(rules.TypeInactiveError())}})

    try:
        duration = rules.compute_duration(employee, time_off_type, payload.start_date, payload.end_date)
    except rules.NoWorkingScheduleError as exc:
        raise HTTPException(400, detail={"error": {"code": "NO_WORKING_SCHEDULE", "message": str(exc)}})
    except rules.NoScheduledWorkingDaysError as exc:
        raise HTTPException(400, detail={"error": {"code": "NO_WORKING_DAYS", "message": str(exc)}})

    if rules.find_overlapping_request(db, employee.id, payload.start_date, payload.end_date) is not None:
        raise HTTPException(409, detail={"error": {"code": "REQUEST_OVERLAP", "message": "This period overlaps another time off request for this employee."}})

    allocation = None
    if time_off_type.requires_allocation:
        try:
            allocation = rules.find_applicable_allocation(db, employee.id, time_off_type.id, payload.start_date, payload.end_date)
        except rules.AmbiguousAllocationError as exc:
            raise HTTPException(409, detail={"error": {"code": "AMBIGUOUS_ALLOCATION", "message": str(exc)}})
        if allocation is None:
            raise HTTPException(404, detail={"error": {"code": "NO_ALLOCATION", "message": str(rules.NoAllocationError(time_off_type.name))}})
        _, remaining = rules.compute_balance(db, allocation)
        if remaining < duration:
            raise HTTPException(409, detail={"error": {"code": "INSUFFICIENT_BALANCE", "message": str(rules.InsufficientBalanceError(time_off_type.name, remaining, duration)), "details": {"available": str(remaining), "requested": str(duration)}}})

    auto_approve = time_off_type.approval_policy.value == "NONE"
    request = TimeOffRequest(
        employee_id=employee.id,
        time_off_type_id=time_off_type.id,
        start_date=payload.start_date,
        end_date=payload.end_date,
        duration_amount=duration,
        reason=payload.reason,
        allocation_id=allocation.id if allocation else None,
        status=RequestStatus.APPROVED if auto_approve else RequestStatus.TO_APPROVE,
        approved_at=rules.now_utc() if auto_approve else None,
    )
    db.add(request)
    db.commit()
    db.refresh(request)
    return _request_response(db, request)


@router.get("/time-off/requests/{request_id}", response_model=TimeOffRequestResponse)
def get_request(request_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    request = db.query(TimeOffRequest).filter(TimeOffRequest.id == request_id).first()
    if not request:
        raise HTTPException(404, detail={"error": {"code": "NOT_FOUND", "message": "Time off request not found."}})
    if current_user.role not in HR_CAPABLE_ROLES and request.employee_id != current_user.employee_id:
        raise HTTPException(403, detail={"error": {"code": "ACCESS_DENIED", "message": "You don't have access to this request."}})
    return _request_response(db, request)


@router.patch("/time-off/requests/{request_id}", response_model=TimeOffRequestResponse)
def update_request(
    request_id: int,
    payload: TimeOffRequestUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    request = db.query(TimeOffRequest).filter(TimeOffRequest.id == request_id).first()
    if not request:
        raise HTTPException(404, detail={"error": {"code": "NOT_FOUND", "message": "Time off request not found."}})
    if current_user.role not in HR_CAPABLE_ROLES and request.employee_id != current_user.employee_id:
        raise HTTPException(403, detail={"error": {"code": "ACCESS_DENIED", "message": "You don't have access to this request."}})
    if request.status != RequestStatus.TO_APPROVE:
        raise HTTPException(409, detail={"error": {"code": "ALREADY_DECIDED", "message": "Only a pending request can be edited."}})

    data = payload.model_dump(exclude_unset=True)
    new_start = data.get("start_date", request.start_date)
    new_end = data.get("end_date", request.end_date)

    if "start_date" in data or "end_date" in data:
        time_off_type = request.time_off_type
        try:
            duration = rules.compute_duration(request.employee, time_off_type, new_start, new_end)
        except rules.NoWorkingScheduleError as exc:
            raise HTTPException(400, detail={"error": {"code": "NO_WORKING_SCHEDULE", "message": str(exc)}})
        except rules.NoScheduledWorkingDaysError as exc:
            raise HTTPException(400, detail={"error": {"code": "NO_WORKING_DAYS", "message": str(exc)}})

        if rules.find_overlapping_request(db, request.employee_id, new_start, new_end, exclude_id=request.id) is not None:
            raise HTTPException(409, detail={"error": {"code": "REQUEST_OVERLAP", "message": "This period overlaps another time off request for this employee."}})

        allocation = None
        if time_off_type.requires_allocation:
            try:
                allocation = rules.find_applicable_allocation(db, request.employee_id, time_off_type.id, new_start, new_end)
            except rules.AmbiguousAllocationError as exc:
                raise HTTPException(409, detail={"error": {"code": "AMBIGUOUS_ALLOCATION", "message": str(exc)}})
            if allocation is None:
                raise HTTPException(404, detail={"error": {"code": "NO_ALLOCATION", "message": str(rules.NoAllocationError(time_off_type.name))}})
            _, remaining = rules.compute_balance(db, allocation)
            if remaining < duration:
                raise HTTPException(409, detail={"error": {"code": "INSUFFICIENT_BALANCE", "message": str(rules.InsufficientBalanceError(time_off_type.name, remaining, duration))}})

        request.start_date = new_start
        request.end_date = new_end
        request.duration_amount = duration
        request.allocation_id = allocation.id if allocation else None

    if "reason" in data:
        request.reason = data["reason"]

    db.commit()
    db.refresh(request)
    return _request_response(db, request)


@router.post("/time-off/requests/{request_id}/approve", response_model=TimeOffRequestResponse)
def approve_request(request_id: int, db: Session = Depends(get_db), current_hr: User = Depends(get_current_hr)):
    request = db.query(TimeOffRequest).filter(TimeOffRequest.id == request_id).first()
    if not request:
        raise HTTPException(404, detail={"error": {"code": "NOT_FOUND", "message": "Time off request not found."}})
    try:
        rules.approve_request(db, request, current_hr)
    except rules.AlreadyDecidedError as exc:
        raise HTTPException(409, detail={"error": {"code": "ALREADY_DECIDED", "message": str(exc)}})
    except rules.SelfApprovalError as exc:
        raise HTTPException(403, detail={"error": {"code": "SELF_APPROVAL", "message": str(exc)}})
    except rules.NoAllocationError as exc:
        raise HTTPException(404, detail={"error": {"code": "NO_ALLOCATION", "message": str(exc)}})
    except rules.InsufficientBalanceError as exc:
        raise HTTPException(409, detail={"error": {"code": "INSUFFICIENT_BALANCE", "message": str(exc)}})
    return _request_response(db, request)


@router.post("/time-off/requests/{request_id}/refuse", response_model=TimeOffRequestResponse)
def refuse_request(request_id: int, db: Session = Depends(get_db), current_hr: User = Depends(get_current_hr)):
    request = db.query(TimeOffRequest).filter(TimeOffRequest.id == request_id).first()
    if not request:
        raise HTTPException(404, detail={"error": {"code": "NOT_FOUND", "message": "Time off request not found."}})
    try:
        rules.refuse_request(db, request, current_hr)
    except rules.AlreadyDecidedError as exc:
        raise HTTPException(409, detail={"error": {"code": "ALREADY_DECIDED", "message": str(exc)}})
    except rules.SelfApprovalError as exc:
        raise HTTPException(403, detail={"error": {"code": "SELF_APPROVAL", "message": str(exc)}})
    return _request_response(db, request)


@router.get("/time-off/balance", response_model=TimeOffBalanceResponse)
def get_balance(
    employee_id: int,
    time_off_type_id: int,
    on_date: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in HR_CAPABLE_ROLES and employee_id != current_user.employee_id:
        raise HTTPException(403, detail={"error": {"code": "ACCESS_DENIED", "message": "You can only view your own balance."}})

    time_off_type = db.query(TimeOffType).filter(TimeOffType.id == time_off_type_id).first()
    if not time_off_type:
        raise HTTPException(404, detail={"error": {"code": "NOT_FOUND", "message": "Time Off Type not found."}})

    target_date = on_date or date.today()
    allocation = (
        db.query(TimeOffAllocation)
        .filter(
            TimeOffAllocation.employee_id == employee_id,
            TimeOffAllocation.time_off_type_id == time_off_type_id,
            TimeOffAllocation.status == AllocationStatus.APPROVED,
            TimeOffAllocation.valid_from <= target_date,
            TimeOffAllocation.valid_to >= target_date,
        )
        .first()
    )
    if allocation is None:
        return TimeOffBalanceResponse(allocation_id=None, unit=time_off_type.unit, allocated=Decimal(0), taken=Decimal(0), remaining=Decimal(0))

    taken, remaining = rules.compute_balance(db, allocation)
    return TimeOffBalanceResponse(allocation_id=allocation.id, unit=time_off_type.unit, allocated=allocation.allocated_amount, taken=taken, remaining=remaining)
