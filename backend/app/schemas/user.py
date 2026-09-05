from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from app.models.user import Role, AccountStatus
from app.schemas.employee import EmployeeResponse

class UserBase(BaseModel):
    work_email: str
    role: Role
    status: AccountStatus

class UserCreate(UserBase):
    employee_id: int
    password: str

class UserUpdate(BaseModel):
    work_email: Optional[EmailStr] = None
    role: Optional[Role] = None
    status: Optional[AccountStatus] = None

class UserResponse(UserBase):
    id: int
    employee_id: int
    employee: Optional[EmployeeResponse] = None
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class LoginRequest(BaseModel):
    email: str
    password: str
