from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base
import enum


class EmployeeStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    employee_code = Column(String, unique=True, index=True, nullable=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    work_email = Column(String, nullable=True)
    work_location = Column(String, nullable=True)
    status = Column(Enum(EmployeeStatus), nullable=False, default=EmployeeStatus.ACTIVE)

    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    job_position_id = Column(Integer, ForeignKey("job_positions.id"), nullable=True)
    manager_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    working_schedule_id = Column(Integer, ForeignKey("working_schedules.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="employee", uselist=False)
    department = relationship("Department", foreign_keys=[department_id])
    job_position = relationship("JobPosition", foreign_keys=[job_position_id])
    working_schedule = relationship("WorkingSchedule", foreign_keys=[working_schedule_id])
    manager = relationship("Employee", remote_side=[id], foreign_keys=[manager_id])
