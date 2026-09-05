from pydantic import BaseModel, field_validator, model_validator
from typing import Optional, List
from datetime import datetime, time
from app.models.working_schedule import ScheduleStatus, DayOfWeek


class WorkingScheduleLineBase(BaseModel):
    day_of_week: DayOfWeek
    start_time: time
    end_time: time
    break_minutes: int = 0

    @field_validator("break_minutes")
    @classmethod
    def break_minutes_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("break_minutes cannot be negative")
        return v

    @model_validator(mode="after")
    def validate_shift(self):
        start_minutes = self.start_time.hour * 60 + self.start_time.minute
        end_minutes = self.end_time.hour * 60 + self.end_time.minute
        if end_minutes <= start_minutes:
            raise ValueError(
                "end_time must be after start_time for the same day; overnight shifts are deferred"
            )
        worked_minutes = end_minutes - start_minutes - self.break_minutes
        if worked_minutes < 0:
            raise ValueError("break_minutes cannot exceed the shift duration")
        return self


class WorkingScheduleLineCreate(WorkingScheduleLineBase):
    pass


class WorkingScheduleLineResponse(WorkingScheduleLineBase):
    id: int
    derived_hours: float

    class Config:
        from_attributes = True


class WorkingScheduleBase(BaseModel):
    name: str
    company: str = "Payloom Inc."
    timezone: str = "Asia/Kolkata"
    status: ScheduleStatus = ScheduleStatus.ACTIVE


class WorkingScheduleCreate(WorkingScheduleBase):
    lines: List[WorkingScheduleLineCreate] = []

    @model_validator(mode="after")
    def validate_lines(self):
        seen_days = set()
        for line in self.lines:
            if line.day_of_week in seen_days:
                raise ValueError(
                    f"duplicate schedule line for {line.day_of_week.value}; "
                    "each day may only appear once per schedule"
                )
            seen_days.add(line.day_of_week)
        return self


class WorkingScheduleUpdate(BaseModel):
    name: Optional[str] = None
    company: Optional[str] = None
    timezone: Optional[str] = None
    status: Optional[ScheduleStatus] = None
    lines: Optional[List[WorkingScheduleLineCreate]] = None

    @model_validator(mode="after")
    def validate_lines(self):
        if self.lines is None:
            return self
        seen_days = set()
        for line in self.lines:
            if line.day_of_week in seen_days:
                raise ValueError(
                    f"duplicate schedule line for {line.day_of_week.value}; "
                    "each day may only appear once per schedule"
                )
            seen_days.add(line.day_of_week)
        return self


class WorkingScheduleSummary(BaseModel):
    id: int
    name: str
    company: str
    status: ScheduleStatus
    days_per_week: int
    hours_per_week: float

    class Config:
        from_attributes = True


class WorkingScheduleResponse(WorkingScheduleBase):
    id: int
    lines: List[WorkingScheduleLineResponse]
    days_per_week: int
    hours_per_week: float
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
