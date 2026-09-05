from sqlalchemy import Column, Integer, DateTime, Date, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class Attendance(Base):
    __tablename__ = "attendances"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)

    # The company-timezone workday this record belongs to (see
    # app/services/attendance_rules.py COMPANY_TZ). One record per
    # employee per attendance_date — not a multi-shift model.
    attendance_date = Column(Date, nullable=False, index=True)

    check_in = Column(DateTime(timezone=True), nullable=False)
    check_out = Column(DateTime(timezone=True), nullable=True)

    notes = Column(Text, nullable=True)
    corrected_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    employee = relationship("Employee", foreign_keys=[employee_id])
    corrected_by = relationship("User", foreign_keys=[corrected_by_user_id])
