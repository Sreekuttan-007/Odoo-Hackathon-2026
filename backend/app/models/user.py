from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base
import enum

class Role(str, enum.Enum):
    EMPLOYEE = "EMPLOYEE"
    HR_MANAGER = "HR_MANAGER"
    HR_PAYROLL_USER = "HR_PAYROLL_USER"
    HR_PAYROLL_MANAGER = "HR_PAYROLL_MANAGER"
    ADMIN = "ADMIN"

class AccountStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), unique=True, nullable=False)
    work_email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(Role), nullable=False, default=Role.EMPLOYEE)
    status = Column(Enum(AccountStatus), nullable=False, default=AccountStatus.ACTIVE)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    employee = relationship("Employee", back_populates="user")
