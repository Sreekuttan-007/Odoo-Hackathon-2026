from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
from app.db.database import get_db
from app.models.attendance import Attendance
from app.models.employee import Employee
from app.models.user import User
from app.schemas.attendance import AttendanceResponse, AttendanceUpdate, CurrentAttendanceResponse
from app.schemas.employee import EmployeeMinimal
from app.api.deps import get_current_user, get_current_hr, HR_CAPABLE_ROLES
from app.services import attendance_rules

router = APIRouter()


def _to_response(db: Session, record: Attendance) -> AttendanceResponse:
    worked_minutes = attendance_rules.derive_worked_minutes(record.check_in, record.check_out)
    corrected_by_name = None
    if record.corrected_by_user_id is not None:
        corrector = db.query(User).filter(User.id == record.corrected_by_user_id).first()
        if corrector and corrector.employee:
            corrected_by_name = f"{corrector.employee.first_name} {corrector.employee.last_name}"

    return AttendanceResponse(
        id=record.id,
        employee=EmployeeMinimal.model_validate(record.employee),
        attendance_date=record.attendance_date.isoformat(),
        check_in=attendance_rules.as_utc(record.check_in),
        check_out=attendance_rules.as_utc(record.check_out) if record.check_out else None,
        worked_minutes=worked_minutes,
        overtime_minutes=attendance_rules.compute_overtime_minutes(record.employee, record.attendance_date, worked_minutes),
        status=attendance_rules.derive_status(record.check_in, record.check_out, record.attendance_date),
        notes=record.notes,
        corrected_by_name=corrected_by_name,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _require_self_employee_id(current_user: User) -> int:
    if current_user.employee_id is None:
        raise HTTPException(400, detail={"error": {"code": "NO_EMPLOYEE_LINK", "message": "Your account isn't linked to an employee record."}})
    return current_user.employee_id


@router.post("/attendance/check-in", response_model=AttendanceResponse)
def check_in(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    employee_id = _require_self_employee_id(current_user)
    try:
        record = attendance_rules.check_in(db, employee_id)
    except attendance_rules.AlreadyCheckedInError as exc:
        raise HTTPException(409, detail={"error": {"code": "ALREADY_CHECKED_IN", "message": str(exc), "details": {"attendance_id": exc.open_session.id}}})
    except attendance_rules.AlreadyRecordedTodayError as exc:
        raise HTTPException(409, detail={"error": {"code": "ALREADY_RECORDED_TODAY", "message": str(exc), "details": {"attendance_id": exc.existing.id}}})
    return _to_response(db, record)


@router.post("/attendance/check-out", response_model=AttendanceResponse)
def check_out(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    employee_id = _require_self_employee_id(current_user)
    try:
        record = attendance_rules.check_out(db, employee_id)
    except attendance_rules.NoOpenSessionError as exc:
        raise HTTPException(409, detail={"error": {"code": "NO_OPEN_SESSION", "message": str(exc)}})
    return _to_response(db, record)


@router.get("/attendance/current", response_model=CurrentAttendanceResponse)
def get_current_attendance(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    employee_id = _require_self_employee_id(current_user)
    record = attendance_rules.get_open_session(db, employee_id)
    if record is None:
        return CurrentAttendanceResponse(checked_in=False, attendance=None)
    return CurrentAttendanceResponse(checked_in=True, attendance=_to_response(db, record))


@router.get("/attendance", response_model=List[AttendanceResponse])
def list_attendance(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    employee_id: Optional[int] = None,
    on_date: Optional[date] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    status: Optional[str] = None,
):
    query = db.query(Attendance)

    if current_user.role not in HR_CAPABLE_ROLES:
        # Self-service: employees may only ever see their own attendance.
        query = query.filter(Attendance.employee_id == current_user.employee_id)
    elif employee_id is not None:
        query = query.filter(Attendance.employee_id == employee_id)

    if on_date is not None:
        query = query.filter(Attendance.attendance_date == on_date)
    if date_from is not None:
        query = query.filter(Attendance.attendance_date >= date_from)
    if date_to is not None:
        query = query.filter(Attendance.attendance_date <= date_to)

    records = query.order_by(Attendance.check_in.desc()).all()
    responses = [_to_response(db, r) for r in records]
    if status:
        responses = [r for r in responses if r.status == status.upper()]
    return responses


@router.get("/attendance/{attendance_id}", response_model=AttendanceResponse)
def get_attendance(
    attendance_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = db.query(Attendance).filter(Attendance.id == attendance_id).first()
    if not record:
        raise HTTPException(404, detail={"error": {"code": "NOT_FOUND", "message": "Attendance record not found."}})
    if current_user.role not in HR_CAPABLE_ROLES and record.employee_id != current_user.employee_id:
        raise HTTPException(403, detail={"error": {"code": "ACCESS_DENIED", "message": "You don't have access to this record."}})
    return _to_response(db, record)


@router.patch("/attendance/{attendance_id}", response_model=AttendanceResponse)
def correct_attendance(
    attendance_id: int,
    payload: AttendanceUpdate,
    db: Session = Depends(get_db),
    current_hr: User = Depends(get_current_hr),
):
    record = db.query(Attendance).filter(Attendance.id == attendance_id).first()
    if not record:
        raise HTTPException(404, detail={"error": {"code": "NOT_FOUND", "message": "Attendance record not found."}})

    data = payload.model_dump(exclude_unset=True)
    new_check_in = attendance_rules.as_utc(data.get("check_in", record.check_in))
    new_check_out = data.get("check_out", record.check_out)
    new_check_out = attendance_rules.as_utc(new_check_out) if new_check_out else None

    if new_check_out is not None and new_check_out < new_check_in:
        raise HTTPException(400, detail={"error": {"code": "INVALID_DATES", "message": "check_out must be on or after check_in."}})

    conflict = attendance_rules.find_overlapping_record(db, record.employee_id, new_check_in, new_check_out, exclude_id=record.id)
    if conflict is not None:
        raise HTTPException(409, detail={
            "error": {
                "code": "ATTENDANCE_OVERLAP",
                "message": f"This correction overlaps another attendance record for this employee ({conflict.attendance_date}).",
                "details": {"conflicting_attendance_id": conflict.id},
            }
        })

    if "check_in" in data:
        record.check_in = new_check_in
        record.attendance_date = attendance_rules.date_in_company_tz(new_check_in)
    if "check_out" in data:
        record.check_out = new_check_out
    if "notes" in data:
        record.notes = data["notes"]
    record.corrected_by_user_id = current_hr.id

    db.commit()
    db.refresh(record)
    return _to_response(db, record)
