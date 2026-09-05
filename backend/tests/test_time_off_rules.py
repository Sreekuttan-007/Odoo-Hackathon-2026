from datetime import date, time
from decimal import Decimal
from types import SimpleNamespace
import pytest
from app.services import time_off_rules as rules
from app.models.working_schedule import DayOfWeek
from app.models.time_off import TimeOffUnit


def _line(day, start, end, break_minutes=0):
    return SimpleNamespace(day_of_week=day, start_time=start, end_time=end, break_minutes=break_minutes)


MON_FRI_9_TO_6 = [
    _line(day, time(9, 0), time(18, 0), 60)
    for day in [DayOfWeek.MONDAY, DayOfWeek.TUESDAY, DayOfWeek.WEDNESDAY, DayOfWeek.THURSDAY, DayOfWeek.FRIDAY]
]


def _employee(schedule_lines=None):
    schedule = SimpleNamespace(lines=schedule_lines) if schedule_lines is not None else None
    return SimpleNamespace(working_schedule=schedule)


def _type(unit=TimeOffUnit.DAYS):
    return SimpleNamespace(unit=unit)


def test_days_duration_counts_scheduled_working_days_only():
    employee = _employee(MON_FRI_9_TO_6)
    # Fri 9 Jan 2026 -> Mon 12 Jan 2026 (inclusive): Fri, Sat, Sun, Mon = 2 working days
    duration = rules.compute_duration(employee, _type(TimeOffUnit.DAYS), date(2026, 1, 9), date(2026, 1, 12))
    assert duration == Decimal(2)


def test_days_duration_five_weekdays():
    employee = _employee(MON_FRI_9_TO_6)
    duration = rules.compute_duration(employee, _type(TimeOffUnit.DAYS), date(2026, 1, 5), date(2026, 1, 9))
    assert duration == Decimal(5)


def test_days_duration_falls_back_to_calendar_days_without_schedule():
    employee = _employee(None)
    duration = rules.compute_duration(employee, _type(TimeOffUnit.DAYS), date(2026, 1, 1), date(2026, 1, 3))
    assert duration == Decimal(3)


def test_days_duration_all_weekend_rejected():
    employee = _employee(MON_FRI_9_TO_6)
    with pytest.raises(rules.NoScheduledWorkingDaysError):
        rules.compute_duration(employee, _type(TimeOffUnit.DAYS), date(2026, 1, 10), date(2026, 1, 11))  # Sat-Sun


def test_hours_duration_sums_expected_hours_per_scheduled_day():
    employee = _employee(MON_FRI_9_TO_6)
    duration = rules.compute_duration(employee, _type(TimeOffUnit.HOURS), date(2026, 1, 5), date(2026, 1, 5))
    assert duration == Decimal(8)


def test_hours_duration_without_schedule_rejected():
    employee = _employee(None)
    with pytest.raises(rules.NoWorkingScheduleError):
        rules.compute_duration(employee, _type(TimeOffUnit.HOURS), date(2026, 1, 5), date(2026, 1, 5))


def test_ranges_overlap_touching_endpoints():
    assert rules.ranges_overlap(date(2026, 9, 12), date(2026, 9, 14), date(2026, 9, 14), date(2026, 9, 16))


def test_ranges_do_not_overlap():
    assert not rules.ranges_overlap(date(2026, 9, 12), date(2026, 9, 13), date(2026, 9, 14), date(2026, 9, 16))
