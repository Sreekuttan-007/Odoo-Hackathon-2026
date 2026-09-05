from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from app.db.database import get_db
from app.models.working_schedule import WorkingSchedule, WorkingScheduleLine, ScheduleStatus
from app.models.user import User
from app.schemas.working_schedule import (
    WorkingScheduleResponse,
    WorkingScheduleLineResponse,
    WorkingScheduleCreate,
    WorkingScheduleUpdate,
)
from app.services.schedule_calculator import compute_line_hours, compute_weekly_summary, sorted_lines
from app.api.deps import get_current_user, get_current_hr

router = APIRouter()


def build_schedule_response(schedule: WorkingSchedule) -> WorkingScheduleResponse:
    lines = sorted_lines(schedule.lines)
    days_per_week, hours_per_week = compute_weekly_summary(lines)
    line_responses = [
        WorkingScheduleLineResponse(
            id=line.id,
            day_of_week=line.day_of_week,
            start_time=line.start_time,
            end_time=line.end_time,
            break_minutes=line.break_minutes,
            derived_hours=compute_line_hours(line.start_time, line.end_time, line.break_minutes),
        )
        for line in lines
    ]
    return WorkingScheduleResponse(
        id=schedule.id,
        name=schedule.name,
        company=schedule.company,
        timezone=schedule.timezone,
        status=schedule.status,
        lines=line_responses,
        days_per_week=days_per_week,
        hours_per_week=hours_per_week,
        created_at=schedule.created_at,
        updated_at=schedule.updated_at,
    )


@router.get("/working-schedules", response_model=List[WorkingScheduleResponse])
def list_working_schedules(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    search: Optional[str] = None,
    status: Optional[ScheduleStatus] = None,
):
    query = db.query(WorkingSchedule)
    if search:
        query = query.filter(WorkingSchedule.name.ilike(f"%{search}%"))
    if status:
        query = query.filter(WorkingSchedule.status == status)
    schedules = query.order_by(WorkingSchedule.name).all()
    return [build_schedule_response(s) for s in schedules]


@router.get("/working-schedules/{schedule_id}", response_model=WorkingScheduleResponse)
def get_working_schedule(
    schedule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    schedule = db.query(WorkingSchedule).filter(WorkingSchedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(404, detail={"error": {"code": "NOT_FOUND", "message": "Working schedule not found."}})
    return build_schedule_response(schedule)


@router.post("/working-schedules", response_model=WorkingScheduleResponse)
def create_working_schedule(
    payload: WorkingScheduleCreate,
    db: Session = Depends(get_db),
    current_hr: User = Depends(get_current_hr),
):
    schedule = WorkingSchedule(
        name=payload.name,
        company=payload.company,
        timezone=payload.timezone,
        status=payload.status,
    )
    db.add(schedule)
    db.flush()

    for line in payload.lines:
        db.add(
            WorkingScheduleLine(
                working_schedule_id=schedule.id,
                day_of_week=line.day_of_week,
                start_time=line.start_time,
                end_time=line.end_time,
                break_minutes=line.break_minutes,
            )
        )
    db.commit()
    db.refresh(schedule)
    return build_schedule_response(schedule)


@router.patch("/working-schedules/{schedule_id}", response_model=WorkingScheduleResponse)
def update_working_schedule(
    schedule_id: int,
    payload: WorkingScheduleUpdate,
    db: Session = Depends(get_db),
    current_hr: User = Depends(get_current_hr),
):
    schedule = db.query(WorkingSchedule).filter(WorkingSchedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(404, detail={"error": {"code": "NOT_FOUND", "message": "Working schedule not found."}})

    if payload.name is not None:
        schedule.name = payload.name
    if payload.company is not None:
        schedule.company = payload.company
    if payload.timezone is not None:
        schedule.timezone = payload.timezone
    if payload.status is not None:
        schedule.status = payload.status

    if payload.lines is not None:
        for existing_line in list(schedule.lines):
            db.delete(existing_line)
        db.flush()
        for line in payload.lines:
            db.add(
                WorkingScheduleLine(
                    working_schedule_id=schedule.id,
                    day_of_week=line.day_of_week,
                    start_time=line.start_time,
                    end_time=line.end_time,
                    break_minutes=line.break_minutes,
                )
            )

    db.commit()
    db.refresh(schedule)
    return build_schedule_response(schedule)
