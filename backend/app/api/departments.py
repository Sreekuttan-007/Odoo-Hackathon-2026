from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List, Optional
from app.db.database import get_db
from app.models.department import Department
from app.models.user import User
from app.schemas.department import DepartmentResponse, DepartmentCreate, DepartmentUpdate
from app.api.deps import get_current_user, get_current_hr

router = APIRouter()


@router.get("/departments", response_model=List[DepartmentResponse])
def list_departments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    search: Optional[str] = None,
):
    query = db.query(Department)
    if search:
        query = query.filter(Department.name.ilike(f"%{search}%"))
    return query.order_by(Department.name).all()


@router.post("/departments", response_model=DepartmentResponse)
def create_department(
    payload: DepartmentCreate,
    db: Session = Depends(get_db),
    current_hr: User = Depends(get_current_hr),
):
    department = Department(name=payload.name)
    db.add(department)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(400, detail={"error": {"code": "ALREADY_EXISTS", "message": "A department with this name already exists."}})
    db.refresh(department)
    return department


@router.patch("/departments/{department_id}", response_model=DepartmentResponse)
def update_department(
    department_id: int,
    payload: DepartmentUpdate,
    db: Session = Depends(get_db),
    current_hr: User = Depends(get_current_hr),
):
    department = db.query(Department).filter(Department.id == department_id).first()
    if not department:
        raise HTTPException(404, detail={"error": {"code": "NOT_FOUND", "message": "Department not found."}})
    if payload.name is not None:
        department.name = payload.name
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(400, detail={"error": {"code": "ALREADY_EXISTS", "message": "A department with this name already exists."}})
    db.refresh(department)
    return department
