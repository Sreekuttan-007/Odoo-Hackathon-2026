from sqlalchemy import Column, Integer, String, DateTime, Date, ForeignKey, Numeric, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class Contract(Base):
    __tablename__ = "contracts"

    id = Column(Integer, primary_key=True, index=True)
    reference = Column(String, unique=True, index=True, nullable=False)

    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False)
    job_position_id = Column(Integer, ForeignKey("job_positions.id"), nullable=False)
    working_schedule_id = Column(Integer, ForeignKey("working_schedules.id"), nullable=True)

    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)

    wage_monthly = Column(Numeric(12, 2), nullable=False)
    currency = Column(String, nullable=False, default="INR")

    # Deferred until the Salary Structure module exists (see docs/DOMAIN_TERMS.md).
    salary_structure_note = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    employee = relationship("Employee", foreign_keys=[employee_id])
    department = relationship("Department", foreign_keys=[department_id])
    job_position = relationship("JobPosition", foreign_keys=[job_position_id])
    working_schedule = relationship("WorkingSchedule", foreign_keys=[working_schedule_id])
