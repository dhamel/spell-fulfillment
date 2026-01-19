"""Task management endpoints."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user
from app.models.task import Task, TaskStatus, TaskPriority, TaskType
from app.schemas.task import (
    TaskCreate,
    TaskDetail,
    TaskList,
    TaskUpdate,
    TaskTypeCreate,
    TaskTypeDetail,
    TaskTypeList,
)

router = APIRouter()


# Task Type endpoints
@router.get("/types", response_model=TaskTypeList)
async def list_task_types(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
) -> TaskTypeList:
    """List all task types."""
    result = await db.execute(select(TaskType).order_by(TaskType.name))
    task_types = result.scalars().all()
    return TaskTypeList(items=task_types)


@router.post("/types", response_model=TaskTypeDetail, status_code=status.HTTP_201_CREATED)
async def create_task_type(
    task_type: TaskTypeCreate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
) -> TaskTypeDetail:
    """Create a custom task type."""
    # Generate slug from name
    slug = task_type.name.lower().replace(" ", "-")

    # Check for duplicate slug
    existing = await db.execute(select(TaskType).where(TaskType.slug == slug))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Task type with this name already exists",
        )

    new_task_type = TaskType(
        name=task_type.name,
        slug=slug,
        description=task_type.description,
        color=task_type.color or "#6B7280",
        is_system=False,
    )

    db.add(new_task_type)
    await db.commit()
    await db.refresh(new_task_type)

    return TaskTypeDetail.model_validate(new_task_type, from_attributes=True)


@router.delete("/types/{task_type_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task_type(
    task_type_id: int,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
) -> None:
    """Delete a custom task type (system types cannot be deleted)."""
    result = await db.execute(select(TaskType).where(TaskType.id == task_type_id))
    task_type = result.scalar_one_or_none()

    if not task_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task type not found",
        )

    if task_type.is_system:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete system task types",
        )

    await db.delete(task_type)
    await db.commit()


# Task endpoints
@router.get("", response_model=TaskList)
async def list_tasks(
    status: Optional[TaskStatus] = None,
    task_type_id: Optional[int] = None,
    priority: Optional[TaskPriority] = None,
    has_order: Optional[bool] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
) -> TaskList:
    """List tasks with optional filters."""
    query = select(Task)

    if status:
        query = query.where(Task.status == status)
    if task_type_id:
        query = query.where(Task.task_type_id == task_type_id)
    if priority:
        query = query.where(Task.priority == priority)
    if has_order is not None:
        if has_order:
            query = query.where(Task.order_id.isnot(None))
        else:
            query = query.where(Task.order_id.is_(None))

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Order by due date (nulls last), then created_at
    query = query.order_by(Task.due_date.asc().nullslast(), Task.created_at.desc())
    query = query.offset((page - 1) * per_page).limit(per_page)

    result = await db.execute(query)
    tasks = result.scalars().all()

    return TaskList(
        items=tasks,
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page,
    )


@router.post("", response_model=TaskDetail, status_code=status.HTTP_201_CREATED)
async def create_task(
    task: TaskCreate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
) -> TaskDetail:
    """Create a new task."""
    # Verify task type exists
    result = await db.execute(select(TaskType).where(TaskType.id == task.task_type_id))
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Task type not found",
        )

    new_task = Task(
        task_type_id=task.task_type_id,
        order_id=task.order_id,
        title=task.title,
        description=task.description,
        priority=task.priority or TaskPriority.MEDIUM,
        due_date=task.due_date,
    )

    db.add(new_task)
    await db.commit()
    await db.refresh(new_task)

    return TaskDetail.model_validate(new_task, from_attributes=True)


@router.get("/{task_id}", response_model=TaskDetail)
async def get_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
) -> TaskDetail:
    """Get task detail."""
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    return TaskDetail.model_validate(task, from_attributes=True)


@router.put("/{task_id}", response_model=TaskDetail)
async def update_task(
    task_id: int,
    task_update: TaskUpdate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
) -> TaskDetail:
    """Update task."""
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    update_data = task_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)

    await db.commit()
    await db.refresh(task)

    return TaskDetail.model_validate(task, from_attributes=True)


@router.patch("/{task_id}/complete", response_model=TaskDetail)
async def complete_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
) -> TaskDetail:
    """Mark task as completed."""
    from datetime import timezone

    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    task.status = TaskStatus.COMPLETED
    task.completed_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(task)

    return TaskDetail.model_validate(task, from_attributes=True)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
) -> None:
    """Delete a task."""
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    await db.delete(task)
    await db.commit()
