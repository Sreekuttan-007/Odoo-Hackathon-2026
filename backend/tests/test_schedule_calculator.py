from datetime import time
from types import SimpleNamespace
import pytest
from app.services.schedule_calculator import compute_line_hours, compute_weekly_summary
from app.models.working_schedule import DayOfWeek


def _line(day, start, end, break_minutes=0):
    return SimpleNamespace(day_of_week=day, start_time=start, end_time=end, break_minutes=break_minutes)


def test_standard_shift_with_break_is_eight_hours():
    assert compute_line_hours(time(9, 0), time(18, 0), 60) == 8.0


def test_five_eight_hour_days_is_forty_weekly_hours():
    lines = [
        _line(day, time(9, 0), time(18, 0), 60)
        for day in [DayOfWeek.MONDAY, DayOfWeek.TUESDAY, DayOfWeek.WEDNESDAY, DayOfWeek.THURSDAY, DayOfWeek.FRIDAY]
    ]
    days_per_week, hours_per_week = compute_weekly_summary(lines)
    assert days_per_week == 5
    assert hours_per_week == 40.0


def test_break_subtracted_from_worked_duration():
    assert compute_line_hours(time(9, 0), time(17, 0), 30) == 7.5


def test_end_before_start_rejected():
    with pytest.raises(ValueError):
        compute_line_hours(time(18, 0), time(9, 0), 0)


def test_end_equal_start_rejected_as_zero_duration():
    with pytest.raises(ValueError):
        compute_line_hours(time(9, 0), time(9, 0), 0)


def test_break_longer_than_shift_rejected():
    with pytest.raises(ValueError):
        compute_line_hours(time(9, 0), time(10, 0), 90)


def test_negative_derived_hours_never_produced():
    # Any accepted line must have non-negative worked duration.
    hours = compute_line_hours(time(9, 0), time(10, 0), 60)
    assert hours >= 0
