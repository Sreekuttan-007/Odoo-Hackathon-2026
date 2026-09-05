from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class JobPositionBase(BaseModel):
    title: str
    level: Optional[int] = None


class JobPositionCreate(JobPositionBase):
    pass


class JobPositionUpdate(BaseModel):
    title: Optional[str] = None
    level: Optional[int] = None


class JobPositionResponse(JobPositionBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
