from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List
from app.db.database import get_db
from app.models.user import User
from app.models.employee import Employee
from app.schemas.user import UserResponse, UserCreate, UserUpdate
from app.schemas.employee import EmployeeMinimal
from app.api.deps import get_current_admin
from app.core.security import get_password_hash

router = APIRouter()

@router.get("/users", response_model=List[UserResponse])
def get_users(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
    search: str = None,
    role: str = None
):
    query = db.query(User).join(Employee)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                User.work_email.ilike(search_term),
                Employee.first_name.ilike(search_term),
                Employee.last_name.ilike(search_term)
            )
        )
    if role:
        query = query.filter(User.role == role)
        
    return query.all()

@router.post("/users", response_model=UserResponse)
def create_user(
    user_in: UserCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    # Check if employee exists and has no user yet
    employee = db.query(Employee).filter(Employee.id == user_in.employee_id).first()
    if not employee:
        raise HTTPException(400, detail={"error": {"code": "NOT_FOUND", "message": "Employee not found."}})
    
    existing_user_emp = db.query(User).filter(User.employee_id == user_in.employee_id).first()
    if existing_user_emp:
        raise HTTPException(400, detail={"error": {"code": "ALREADY_EXISTS", "message": "Employee already has an account."}})
        
    existing_user_email = db.query(User).filter(User.work_email == user_in.work_email).first()
    if existing_user_email:
        raise HTTPException(400, detail={"error": {"code": "ALREADY_EXISTS", "message": "Email already in use."}})

    new_user = User(
        employee_id=user_in.employee_id,
        work_email=user_in.work_email,
        hashed_password=get_password_hash(user_in.password),
        role=user_in.role,
        status=user_in.status
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.put("/users/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user_in: UserUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, detail={"error": {"code": "NOT_FOUND", "message": "User not found."}})
        
    if user_in.work_email and user_in.work_email != user.work_email:
        existing = db.query(User).filter(User.work_email == user_in.work_email).first()
        if existing:
            raise HTTPException(400, detail={"error": {"code": "ALREADY_EXISTS", "message": "Email already in use."}})
        user.work_email = user_in.work_email
        
    if user_in.role:
        user.role = user_in.role
    if user_in.status:
        user.status = user_in.status
        
    db.commit()
    db.refresh(user)
    return user

@router.get("/employees/lookup", response_model=List[EmployeeMinimal])
def get_employees_for_lookup(db: Session = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    # Return employees that don't have a user account
    employees = db.query(Employee).outerjoin(User).filter(User.id == None).all()
    return employees
