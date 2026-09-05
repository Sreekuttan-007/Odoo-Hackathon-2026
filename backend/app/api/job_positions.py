from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List, Optional
from app.db.database import get_db
from app.models.job_position import JobPosition
from app.models.user import User
from app.schemas.job_position import JobPositionResponse, JobPositionCreate, JobPositionUpdate
from app.api.deps import get_current_user, get_current_hr

router = APIRouter()


@router.get("/job-positions", response_model=List[JobPositionResponse])
def list_job_positions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    search: Optional[str] = None,
):
    query = db.query(JobPosition)
    if search:
        query = query.filter(JobPosition.title.ilike(f"%{search}%"))
    return query.order_by(JobPosition.title).all()


@router.post("/job-positions", response_model=JobPositionResponse)
def create_job_position(
    payload: JobPositionCreate,
    db: Session = Depends(get_db),
    current_hr: User = Depends(get_current_hr),
):
    job_position = JobPosition(title=payload.title)
    db.add(job_position)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(400, detail={"error": {"code": "ALREADY_EXISTS", "message": "A job position with this title already exists."}})
    db.refresh(job_position)
    return job_position


@router.patch("/job-positions/{job_position_id}", response_model=JobPositionResponse)
def update_job_position(
    job_position_id: int,
    payload: JobPositionUpdate,
    db: Session = Depends(get_db),
    current_hr: User = Depends(get_current_hr),
):
    job_position = db.query(JobPosition).filter(JobPosition.id == job_position_id).first()
    if not job_position:
        raise HTTPException(404, detail={"error": {"code": "NOT_FOUND", "message": "Job position not found."}})
    if payload.title is not None:
        job_position.title = payload.title
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(400, detail={"error": {"code": "ALREADY_EXISTS", "message": "A job position with this title already exists."}})
    db.refresh(job_position)
    return job_position
