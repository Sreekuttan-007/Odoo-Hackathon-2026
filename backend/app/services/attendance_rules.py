"""Attendance business rules.

Policy (documented per docs/DOMAIN_TERMS.md):
- Working Schedule = expected time. Attendance = actual time. Attendance
  never mutates Working Schedule.
- One Attendance record per employee per COMPANY-TIMEZONE day (Asia/Kolkata),
  not a multi-shift model. "Today" and the record's attendance_date are both
  computed in this timezone, never naive/UTC-midnight.
- All timestamps are stored in UTC (timezone-aware). The company timezone is
  only used to bucket a check-in into a calendar day and to answer "is this
  today".
- worked_minutes, session status, and overtime are DERIVED from timestamps
  on every read — never persisted — so they can never drift out of sync
  with a correction.
- Check-in is rejected if the employee already has an open session (any
  date — catches a stale missing-checkout) or already has a record for
  today (the one-record-per-day rule).
- Corrections may only change check_in/check_out/notes; worked_minutes is
  never independently editable. A correction must still satisfy
  check_out >= check_in and must not overlap another Attendance record for
  the same employee.
"""
from datetime import date, datetime, timezone
from typing import Optional
from zoneinfo import ZoneInfo
from sqlalchemy.orm import Session
from app.models.attendance import Attendance
from app.models.employee import Employee
from app.models.working_schedule import DayOfWeek

COMPANY_TZ = ZoneInfo("Asia/Kolkata")

_WEEKDAY_TO_DAY_OF_WEEK = {
    0: DayOfWeek.MONDAY,
    1: DayOfWeek.TUESDAY,
    2: DayOfWeek.WEDNESDAY,
    3: DayOfWeek.THURSDAY,
    4: DayOfWeek.FRIDAY,
    5: DayOfWeek.SATURDAY,
    6: DayOfWeek.SUNDAY,
}


class AttendanceOverlapError(ValueError):
    def __init__(self, conflicting: Attendance):
        self.conflicting = conflicting
        super().__init__(
            f"This attendance record overlaps another record for this employee on {conflicting.attendance_date}."
        )


class AlreadyCheckedInError(ValueError):
    def __init__(self, open_session: Attendance):
        self.open_session = open_session
        super().__init__("This employee already has an open attendance session.")


class AlreadyRecordedTodayError(ValueError):
    def __init__(self, existing: Attendance):
        self.existing = existing
        super().__init__("This employee already has an attendance record for today.")


class NoOpenSessionError(ValueError):
    def __init__(self):
        super().__init__("No open attendance session to check out of.")


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def as_utc(moment: datetime) -> datetime:
    """SQLite drops tzinfo on round-trip, so any datetime read back from the
    database comes back naive. Every value that was written here was written
    as UTC (now_utc()), so a naive value is always safe to assume-UTC.
    Client-supplied correction timestamps are also normalized here, so a
    naive request body is likewise treated as UTC rather than raising when
    compared against an aware value."""
    if moment.tzinfo is None:
        return moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc)


def today_in_company_tz() -> date:
    return datetime.now(COMPANY_TZ).date()


def date_in_company_tz(moment: datetime) -> date:
    return as_utc(moment).astimezone(COMPANY_TZ).date()


def derive_worked_minutes(check_in: datetime, check_out: Optional[datetime]) -> Optional[int]:
    if check_out is None:
        return None
    return max(0, int((as_utc(check_out) - as_utc(check_in)).total_seconds() // 60))


def derive_status(check_in: datetime, check_out: Optional[datetime], attendance_date: date) -> str:
    if check_out is not None:
        return "COMPLETED"
    if attendance_date < today_in_company_tz():
        return "MISSING_CHECKOUT"
    return "ACTIVE"


def compute_overtime_minutes(employee: Employee, attendance_date: date, worked_minutes: Optional[int]) -> Optional[int]:
    """Deterministic overtime: worked_minutes - expected_minutes for that
    weekday, per the employee's Working Schedule. Returns None (not faked)
    when the employee has no schedule or no line for that weekday."""
    if worked_minutes is None:
        return None
    schedule = employee.working_schedule
    if schedule is None:
        return None
    day_of_week = _WEEKDAY_TO_DAY_OF_WEEK[attendance_date.weekday()]
    line = next((l for l in schedule.lines if l.day_of_week == day_of_week), None)
    if line is None:
        return None
    expected_minutes = (
        (line.end_time.hour * 60 + line.end_time.minute)
        - (line.start_time.hour * 60 + line.start_time.minute)
        - line.break_minutes
    )
    return max(0, worked_minutes - expected_minutes)


def _effective_range(record: Attendance) -> tuple[datetime, datetime]:
    return as_utc(record.check_in), as_utc(record.check_out) if record.check_out else now_utc()


def _ranges_overlap(start_a: datetime, end_a: datetime, start_b: datetime, end_b: datetime) -> bool:
    return start_a <= end_b and start_b <= end_a


def find_overlapping_record(
    db: Session, employee_id: int, check_in: datetime, check_out: Optional[datetime], exclude_id: Optional[int] = None
) -> Optional[Attendance]:
    start = as_utc(check_in)
    end = as_utc(check_out) if check_out else now_utc()
    query = db.query(Attendance).filter(Attendance.employee_id == employee_id)
    if exclude_id is not None:
        query = query.filter(Attendance.id != exclude_id)
    for existing in query.all():
        existing_start, existing_end = _effective_range(existing)
        if _ranges_overlap(start, end, existing_start, existing_end):
            return existing
    return None


def get_open_session(db: Session, employee_id: int) -> Optional[Attendance]:
    return (
        db.query(Attendance)
        .filter(Attendance.employee_id == employee_id, Attendance.check_out.is_(None))
        .order_by(Attendance.check_in.desc())
        .first()
    )


def assert_can_check_in(db: Session, employee_id: int) -> None:
    open_session = get_open_session(db, employee_id)
    if open_session is not None:
        raise AlreadyCheckedInError(open_session)

    today = today_in_company_tz()
    existing_today = (
        db.query(Attendance)
        .filter(Attendance.employee_id == employee_id, Attendance.attendance_date == today)
        .first()
    )
    if existing_today is not None:
        raise AlreadyRecordedTodayError(existing_today)


def check_in(db: Session, employee_id: int) -> Attendance:
    assert_can_check_in(db, employee_id)
    moment = now_utc()
    record = Attendance(
        employee_id=employee_id,
        attendance_date=date_in_company_tz(moment),
        check_in=moment,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def check_out(db: Session, employee_id: int) -> Attendance:
    record = get_open_session(db, employee_id)
    if record is None:
        raise NoOpenSessionError()
    record.check_out = now_utc()
    db.commit()
    db.refresh(record)
    return record
