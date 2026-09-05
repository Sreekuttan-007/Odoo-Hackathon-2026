"""Working Schedule hour calculation.

A line's worked duration = end_time - start_time - break_minutes.
A schedule's weekly hours = sum of every line's worked duration.
Overnight shifts (end_time <= start_time) are deferred and rejected outright
rather than silently miscalculated.
"""
from datetime import time
from typing import Iterable, Tuple
from app.models.working_schedule import DayOfWeek, DAY_ORDER


def compute_line_hours(start_time: time, end_time: time, break_minutes: int) -> float:
    start_minutes = start_time.hour * 60 + start_time.minute
    end_minutes = end_time.hour * 60 + end_time.minute

    if end_minutes <= start_minutes:
        raise ValueError(
            "end_time must be after start_time for the same day; overnight shifts are deferred"
        )

    worked_minutes = end_minutes - start_minutes - break_minutes
    if worked_minutes < 0:
        raise ValueError("break_minutes cannot exceed the shift duration")

    return round(worked_minutes / 60, 2)


def compute_weekly_summary(lines: Iterable) -> Tuple[int, float]:
    days = {line.day_of_week for line in lines}
    total_hours = sum(
        compute_line_hours(line.start_time, line.end_time, line.break_minutes) for line in lines
    )
    return len(days), round(total_hours, 2)


def sorted_lines(lines: Iterable) -> list:
    return sorted(lines, key=lambda line: DAY_ORDER[DayOfWeek(line.day_of_week)])


def build_schedule_summary(schedule):
    """Build a WorkingScheduleSummary for nesting inside Employee/Contract
    responses, without importing those schemas (avoids import cycles)."""
    from app.schemas.working_schedule import WorkingScheduleSummary

    if schedule is None:
        return None
    days_per_week, hours_per_week = compute_weekly_summary(schedule.lines)
    return WorkingScheduleSummary(
        id=schedule.id,
        name=schedule.name,
        company=schedule.company,
        status=schedule.status,
        days_per_week=days_per_week,
        hours_per_week=hours_per_week,
    )
