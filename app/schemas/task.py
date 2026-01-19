"""Task schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.models.task import TaskPriority, TaskStatus


class TaskTypeCreate(BaseModel):
    """Create custom task type."""

    name: str
    description: Optional[str] = None
    color: Optional[str] = None


class TaskTypeDetail(BaseModel):
    """Task type detail."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    description: Optional[str]
    color: str
    is_system: bool


class TaskTypeList(BaseModel):
    """List of task types."""

    items: list[TaskTypeDetail]


class TaskCreate(BaseModel):
    """Create a task."""

    task_type_id: int
    title: str
    description: Optional[str] = None
    priority: Optional[TaskPriority] = TaskPriority.MEDIUM
    due_date: Optional[datetime] = None
    order_id: Optional[int] = None


class TaskUpdate(BaseModel):
    """Update a task."""

    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    due_date: Optional[datetime] = None


class TaskDetail(BaseModel):
    """Task detail."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    task_type_id: int
    order_id: Optional[int]
    title: str
    description: Optional[str]
    status: TaskStatus
    priority: TaskPriority
    due_date: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class TaskList(BaseModel):
    """Paginated task list."""

    items: list[TaskDetail]
    total: int
    page: int
    per_page: int
    pages: int
