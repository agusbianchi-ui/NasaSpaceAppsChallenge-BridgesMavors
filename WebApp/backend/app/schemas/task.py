from typing import List, Optional
from pydantic import BaseModel, Field, conint


class Task(BaseModel):
    id: str = Field(default_factory=lambda: f"TASK-{__import__('uuid').uuid4().hex[:8].upper()}")
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="", max_length=1000)
    priority: conint(ge=1, le=4) = 2  # 1=Low, 2=Medium, 3=High, 4=Critical
    status: str = Field("BACKLOG", max_length=20)
    target_id: Optional[str] = Field(None, max_length=20)
    due_date: Optional[str] = Field(None, max_length=10)
    created_at: str = Field(default_factory=lambda: __import__('datetime').datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: __import__('datetime').datetime.utcnow().isoformat())

    class Config:
        schema_extra = {
            "example": {
                "id": "TASK-001",
                "title": "Rock Analysis",
                "description": "Analyze sample from JZ-001 outcrop",
                "priority": 3,
                "status": "TO_DO",
                "target_id": "JZ-001",
                "due_date": "2025-02-01",
            }
        }


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="", max_length=1000)
    priority: conint(ge=1, le=4) = 2
    status: str = Field("BACKLOG", max_length=20)
    target_id: Optional[str] = Field(None, max_length=20)
    due_date: Optional[str] = Field(None, max_length=10)


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    priority: Optional[conint(ge=1, le=4)] = None
    status: Optional[str] = Field(None, max_length=20)
    target_id: Optional[str] = Field(None, max_length=20)
    due_date: Optional[str] = Field(None, max_length=10)


class TaskResponse(Task):
    id: str
    title: str
    description: str
    priority: int
    status: str
    target_id: Optional[str]
    due_date: Optional[str]
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True