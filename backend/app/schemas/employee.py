from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class EmployeeBase(BaseModel):
    first_name: str
    last_name: str
    work_email: Optional[str] = None
    department: Optional[str] = None

class EmployeeResponse(EmployeeBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True
