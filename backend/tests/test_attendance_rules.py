from datetime import date, time, datetime, timezone, timedelta
import pytest
from app.models.employee import Employee
from app.models.attendance import Attendance
from app.models.working_schedule import WorkingSchedule, WorkingScheduleLine, DayOfWeek, ScheduleStatus
from app.services import attendance_rules


def _make_employee(db_session):
    emp = Employee(first_name="Test", last_name="Worker", work_email="worker@payloom.local")
    db_session.add(emp)
    db_session.flush()
    return emp


def test_check_in_creates_attendance(db_session):
    emp = _make_employee(db_session)
    record = attendance_rules.check_in(db_session, emp.id)
    assert record.employee_id == emp.id
    assert record.check_out is None
    assert record.attendance_date == attendance_rules.today_in_company_tz()


def test_second_check_in_while_open_rejected(db_session):
    emp = _make_employee(db_session)
    attendance_rules.check_in(db_session, emp.id)
    with pytest.raises(attendance_rules.AlreadyCheckedInError):
        attendance_rules.check_in(db_session, emp.id)


def test_check_out_no_open_session_rejected(db_session):
    emp = _make_employee(db_session)
    with pytest.raises(attendance_rules.NoOpenSessionError):
        attendance_rules.check_out(db_session, emp.id)


def test_check_out_calculates_worked_duration():
    check_in = datetime(2026, 1, 1, 9, 5, tzinfo=timezone.utc)
    check_out = datetime(2026, 1, 1, 18, 10, tzinfo=timezone.utc)
    assert attendance_rules.derive_worked_minutes(check_in, check_out) == 9 * 60 + 5


def test_open_session_worked_minutes_is_none():
    check_in = datetime(2026, 1, 1, 9, 5, tzinfo=timezone.utc)
    assert attendance_rules.derive_worked_minutes(check_in, None) is None


def test_naive_datetimes_from_db_do_not_crash_comparisons(db_session):
    # Simulates SQLite's tzinfo-stripping round-trip: as_utc() must make a
    # naive value (assumed UTC) safely comparable with a fresh aware one.
    naive_check_in = datetime(2026, 1, 1, 9, 0)
    aware_now = attendance_rules.now_utc()
    assert attendance_rules.as_utc(naive_check_in) <= aware_now


def test_overlapping_attendance_rejected(db_session):
    emp = _make_employee(db_session)
    existing = Attendance(
        employee_id=emp.id, attendance_date=date(2026, 1, 1),
        check_in=datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc),
        check_out=datetime(2026, 1, 1, 18, 0, tzinfo=timezone.utc),
    )
    db_session.add(existing)
    db_session.commit()

    conflict = attendance_rules.find_overlapping_record(
        db_session, emp.id,
        datetime(2026, 1, 1, 17, 0, tzinfo=timezone.utc),
        datetime(2026, 1, 1, 19, 0, tzinfo=timezone.utc),
    )
    assert conflict is not None
    assert conflict.id == existing.id


def test_non_overlapping_attendance_allowed(db_session):
    emp = _make_employee(db_session)
    existing = Attendance(
        employee_id=emp.id, attendance_date=date(2026, 1, 1),
        check_in=datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc),
        check_out=datetime(2026, 1, 1, 18, 0, tzinfo=timezone.utc),
    )
    db_session.add(existing)
    db_session.commit()

    conflict = attendance_rules.find_overlapping_record(
        db_session, emp.id,
        datetime(2026, 1, 2, 9, 0, tzinfo=timezone.utc),
        datetime(2026, 1, 2, 18, 0, tzinfo=timezone.utc),
    )
    assert conflict is None


def test_missing_checkout_status_for_stale_open_session():
    old_date = attendance_rules.today_in_company_tz() - timedelta(days=2)
    status = attendance_rules.derive_status(
        check_in=datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc), check_out=None, attendance_date=old_date,
    )
    assert status == "MISSING_CHECKOUT"


def test_active_status_for_todays_open_session():
    today = attendance_rules.today_in_company_tz()
    status = attendance_rules.derive_status(
        check_in=datetime.now(timezone.utc), check_out=None, attendance_date=today,
    )
    assert status == "ACTIVE"


def test_completed_status_when_checked_out():
    status = attendance_rules.derive_status(
        check_in=datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc),
        check_out=datetime(2026, 1, 1, 18, 0, tzinfo=timezone.utc),
        attendance_date=date(2026, 1, 1),
    )
    assert status == "COMPLETED"


def _make_schedule(db_session):
    schedule = WorkingSchedule(name="40 Hours / Week", status=ScheduleStatus.ACTIVE)
    db_session.add(schedule)
    db_session.flush()
    db_session.add(WorkingScheduleLine(
        working_schedule_id=schedule.id, day_of_week=DayOfWeek.THURSDAY,
        start_time=time(9, 0), end_time=time(18, 0), break_minutes=60,
    ))
    db_session.commit()
    return schedule


def test_overtime_computed_against_matching_schedule_day(db_session):
    emp = _make_employee(db_session)
    emp.working_schedule = _make_schedule(db_session)
    thursday = date(2026, 1, 1)  # 2026-01-01 is a Thursday
    assert thursday.weekday() == 3
    overtime = attendance_rules.compute_overtime_minutes(emp, thursday, worked_minutes=540)  # 9h worked
    assert overtime == 60  # expected 8h -> 60min overtime


def test_no_overtime_within_expected_hours(db_session):
    emp = _make_employee(db_session)
    emp.working_schedule = _make_schedule(db_session)
    thursday = date(2026, 1, 1)
    overtime = attendance_rules.compute_overtime_minutes(emp, thursday, worked_minutes=400)
    assert overtime == 0


def test_overtime_none_when_no_schedule(db_session):
    emp = _make_employee(db_session)
    overtime = attendance_rules.compute_overtime_minutes(emp, date(2026, 1, 1), worked_minutes=540)
    assert overtime is None


def test_overtime_none_when_day_not_in_schedule(db_session):
    emp = _make_employee(db_session)
    emp.working_schedule = _make_schedule(db_session)  # only Thursday has a line
    saturday = date(2026, 1, 3)
    assert saturday.weekday() == 5
    overtime = attendance_rules.compute_overtime_minutes(emp, saturday, worked_minutes=540)
    assert overtime is None


def test_overtime_none_when_still_checked_in(db_session):
    emp = _make_employee(db_session)
    emp.working_schedule = _make_schedule(db_session)
    overtime = attendance_rules.compute_overtime_minutes(emp, date(2026, 1, 1), worked_minutes=None)
    assert overtime is None
