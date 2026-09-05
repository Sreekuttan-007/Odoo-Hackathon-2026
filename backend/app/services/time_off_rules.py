"""Time Off business rules: duration calculation, allocation resolution,
and the exactly-once balance consumption rule.

Policy (documented per docs/DOMAIN_TERMS.md):
- TimeOffType defines policy (unit, approval, whether allocation is
  required). TimeOffAllocation defines entitlement. TimeOffRequest
  represents actual usage and consumes entitlement ONLY after approval.
- Balance is never persisted. `taken` is always the sum of `duration_amount`
  for APPROVED TimeOffRequests linked to an allocation; `remaining` is
  `allocated_amount - taken`. Pending/refused requests contribute 0.
- Duration is computed once, at request creation time, from the employee's
  Working Schedule (a snapshot — see TimeOffRequest.duration_amount). For
  DAYS-unit types this counts scheduled working days in the period; for
  HOURS-unit types it sums each scheduled day's expected hours. If the
  employee has no Working Schedule: DAYS falls back to a calendar-day count
  (documented fallback, not silent); HOURS has no safe fallback and is
  rejected outright with NoWorkingScheduleError.
- Approval is a single backend transaction: re-validate the request is still
  TO_APPROVE, re-resolve the allocation, re-check remaining balance, then
  mark APPROVED. Calling approve on an already-decided request always fails
  fast (AlreadyDecidedError) rather than silently no-op'ing, which is what
  makes double-approval structurally unable to double-deduct.
- One APPROVED allocation per (employee, type, validity period) is
  enforced at approval time, not just creation, since creation may precede
  approval by any amount of time.
"""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional, Sequence
from sqlalchemy.orm import Session
from app.models.employee import Employee
from app.models.time_off import (
    TimeOffType, TimeOffAllocation, TimeOffRequest,
    TimeOffUnit, AllocationStatus, RequestStatus,
)
from app.models.working_schedule import DayOfWeek

_WEEKDAY_TO_DAY_OF_WEEK = {
    0: DayOfWeek.MONDAY, 1: DayOfWeek.TUESDAY, 2: DayOfWeek.WEDNESDAY,
    3: DayOfWeek.THURSDAY, 4: DayOfWeek.FRIDAY, 5: DayOfWeek.SATURDAY, 6: DayOfWeek.SUNDAY,
}


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class TypeInactiveError(ValueError):
    def __init__(self):
        super().__init__("This Time Off Type is inactive and cannot be used for new requests.")


class InvalidPeriodError(ValueError):
    def __init__(self, message: str = "end_date must be on or after start_date."):
        super().__init__(message)


class NoWorkingScheduleError(ValueError):
    def __init__(self):
        super().__init__("Cannot compute hourly leave duration without a Working Schedule.")


class NoScheduledWorkingDaysError(ValueError):
    def __init__(self):
        super().__init__("This period contains no scheduled working days for this employee.")


class NoAllocationError(ValueError):
    def __init__(self, type_name: str):
        super().__init__(f"No approved {type_name} allocation covers this period.")


class AmbiguousAllocationError(ValueError):
    def __init__(self, allocations: Sequence[TimeOffAllocation]):
        self.allocations = list(allocations)
        super().__init__("Multiple approved allocations are applicable for this period.")


class InsufficientBalanceError(ValueError):
    def __init__(self, type_name: str, available: Decimal, requested: Decimal):
        self.available = available
        self.requested = requested
        super().__init__(
            f"Insufficient {type_name} balance. {available} available, {requested} requested."
        )


class RequestOverlapError(ValueError):
    def __init__(self, conflicting: TimeOffRequest):
        self.conflicting = conflicting
        super().__init__("This period overlaps another time off request for this employee.")


class AllocationOverlapError(ValueError):
    def __init__(self, conflicting: TimeOffAllocation):
        self.conflicting = conflicting
        super().__init__("Another approved allocation for this employee/type already covers an overlapping period.")


class AlreadyDecidedError(ValueError):
    def __init__(self, current_status: str):
        self.current_status = current_status
        super().__init__(f"This item has already been decided ({current_status}).")


class SelfApprovalError(ValueError):
    def __init__(self):
        super().__init__("You cannot approve or refuse your own request.")


class UnitLockedError(ValueError):
    def __init__(self):
        super().__init__("This Time Off Type's unit cannot change once it has allocations or requests.")


def ranges_overlap(start_a: date, end_a: date, start_b: date, end_b: date) -> bool:
    return start_a <= end_b and start_b <= end_a


def scheduled_working_days(employee: Employee, start_date: date, end_date: date) -> list[date]:
    schedule = employee.working_schedule
    if schedule is None:
        return []
    line_days = {line.day_of_week for line in schedule.lines}
    days = []
    current = start_date
    while current <= end_date:
        if _WEEKDAY_TO_DAY_OF_WEEK[current.weekday()] in line_days:
            days.append(current)
        current += timedelta(days=1)
    return days


def compute_duration(employee: Employee, time_off_type: TimeOffType, start_date: date, end_date: date) -> Decimal:
    """Deterministic duration for a request period. See module docstring."""
    if end_date < start_date:
        raise InvalidPeriodError()

    schedule = employee.working_schedule
    scheduled_days = scheduled_working_days(employee, start_date, end_date)

    if time_off_type.unit == TimeOffUnit.HOURS:
        if schedule is None:
            raise NoWorkingScheduleError()
        line_by_day = {line.day_of_week: line for line in schedule.lines}
        total_minutes = 0
        for day in scheduled_days:
            line = line_by_day[_WEEKDAY_TO_DAY_OF_WEEK[day.weekday()]]
            expected = (
                (line.end_time.hour * 60 + line.end_time.minute)
                - (line.start_time.hour * 60 + line.start_time.minute)
                - line.break_minutes
            )
            total_minutes += max(0, expected)
        if total_minutes == 0:
            raise NoScheduledWorkingDaysError()
        return Decimal(total_minutes) / Decimal(60)

    # DAYS
    if schedule is None:
        # Documented fallback: no schedule to consult, so count calendar days
        # inclusive rather than guessing which are "working days".
        return Decimal((end_date - start_date).days + 1)
    if not scheduled_days:
        raise NoScheduledWorkingDaysError()
    return Decimal(len(scheduled_days))


def find_overlapping_request(
    db: Session, employee_id: int, start_date: date, end_date: date, exclude_id: Optional[int] = None
) -> Optional[TimeOffRequest]:
    query = db.query(TimeOffRequest).filter(
        TimeOffRequest.employee_id == employee_id,
        TimeOffRequest.status.in_([RequestStatus.TO_APPROVE, RequestStatus.APPROVED]),
    )
    if exclude_id is not None:
        query = query.filter(TimeOffRequest.id != exclude_id)
    for existing in query.all():
        if ranges_overlap(start_date, end_date, existing.start_date, existing.end_date):
            return existing
    return None


def find_overlapping_allocation(
    db: Session, employee_id: int, time_off_type_id: int, valid_from: date, valid_to: date, exclude_id: Optional[int] = None
) -> Optional[TimeOffAllocation]:
    query = db.query(TimeOffAllocation).filter(
        TimeOffAllocation.employee_id == employee_id,
        TimeOffAllocation.time_off_type_id == time_off_type_id,
        TimeOffAllocation.status == AllocationStatus.APPROVED,
    )
    if exclude_id is not None:
        query = query.filter(TimeOffAllocation.id != exclude_id)
    for existing in query.all():
        if ranges_overlap(valid_from, valid_to, existing.valid_from, existing.valid_to):
            return existing
    return None


def find_applicable_allocation(
    db: Session, employee_id: int, time_off_type_id: int, start_date: date, end_date: date
) -> Optional[TimeOffAllocation]:
    """An allocation is applicable if it is APPROVED and its validity period
    fully covers [start_date, end_date]. Enforcing uniqueness at approval
    time (find_overlapping_allocation) means this should never return more
    than one match — but a data state from before that rule existed is
    still detected and reported, never silently resolved."""
    candidates = (
        db.query(TimeOffAllocation)
        .filter(
            TimeOffAllocation.employee_id == employee_id,
            TimeOffAllocation.time_off_type_id == time_off_type_id,
            TimeOffAllocation.status == AllocationStatus.APPROVED,
            TimeOffAllocation.valid_from <= start_date,
            TimeOffAllocation.valid_to >= end_date,
        )
        .all()
    )
    if len(candidates) > 1:
        raise AmbiguousAllocationError(candidates)
    return candidates[0] if candidates else None


def compute_balance(db: Session, allocation: TimeOffAllocation) -> tuple[Decimal, Decimal]:
    """Returns (taken, remaining) for an allocation. Only APPROVED requests
    linked to this allocation count toward `taken` — pending/refused
    requests never reduce the available balance."""
    if allocation.status != AllocationStatus.APPROVED:
        return Decimal(0), Decimal(0)
    approved_requests = (
        db.query(TimeOffRequest)
        .filter(TimeOffRequest.allocation_id == allocation.id, TimeOffRequest.status == RequestStatus.APPROVED)
        .all()
    )
    taken = sum((r.duration_amount for r in approved_requests), Decimal(0))
    remaining = allocation.allocated_amount - taken
    return taken, remaining


def approve_allocation(db: Session, allocation: TimeOffAllocation, approver_id: int) -> TimeOffAllocation:
    if allocation.status != AllocationStatus.TO_APPROVE:
        raise AlreadyDecidedError(allocation.status.value)
    conflict = find_overlapping_allocation(
        db, allocation.employee_id, allocation.time_off_type_id, allocation.valid_from, allocation.valid_to, exclude_id=allocation.id
    )
    if conflict is not None:
        raise AllocationOverlapError(conflict)
    allocation.status = AllocationStatus.APPROVED
    allocation.approver_user_id = approver_id
    allocation.approved_at = now_utc()
    db.commit()
    db.refresh(allocation)
    return allocation


def refuse_allocation(db: Session, allocation: TimeOffAllocation, approver_id: int) -> TimeOffAllocation:
    if allocation.status != AllocationStatus.TO_APPROVE:
        raise AlreadyDecidedError(allocation.status.value)
    allocation.status = AllocationStatus.REFUSED
    allocation.approver_user_id = approver_id
    db.commit()
    db.refresh(allocation)
    return allocation


def approve_request(db: Session, request: TimeOffRequest, approver_user) -> TimeOffRequest:
    if request.status != RequestStatus.TO_APPROVE:
        raise AlreadyDecidedError(request.status.value)
    if request.employee.user is not None and request.employee.user.id == approver_user.id:
        raise SelfApprovalError()

    if request.time_off_type.requires_allocation:
        allocation = request.allocation
        if allocation is None or allocation.status != AllocationStatus.APPROVED:
            raise NoAllocationError(request.time_off_type.name)
        taken, remaining = compute_balance(db, allocation)
        if remaining < request.duration_amount:
            raise InsufficientBalanceError(request.time_off_type.name, remaining, request.duration_amount)

    request.status = RequestStatus.APPROVED
    request.approver_user_id = approver_user.id
    request.approved_at = now_utc()
    db.commit()
    db.refresh(request)
    return request


def refuse_request(db: Session, request: TimeOffRequest, approver_user) -> TimeOffRequest:
    if request.status != RequestStatus.TO_APPROVE:
        raise AlreadyDecidedError(request.status.value)
    if request.employee.user is not None and request.employee.user.id == approver_user.id:
        raise SelfApprovalError()
    request.status = RequestStatus.REFUSED
    request.approver_user_id = approver_user.id
    request.refused_at = now_utc()
    db.commit()
    db.refresh(request)
    return request
