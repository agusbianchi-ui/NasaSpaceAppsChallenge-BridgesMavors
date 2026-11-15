from fastapi import APIRouter, Body, HTTPException, Path, Query
from typing import List

from app.schemas.task import Task, TaskCreate, TaskUpdate, TaskResponse
from app.services.task_service import (
    create_task,
    delete_task,
    get_task,
    list_tasks,
    update_task,
    get_task_by_target,
)

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.get("/", response_model=List[TaskResponse], summary="List all tasks")
def list_tasks_endpoint() -> List[TaskResponse]:
    """Retrieve all tasks, sorted by creation date (newest first)."""
    return list_tasks()


@router.get("/{task_id}", response_model=TaskResponse, summary="Get task by ID")
def get_task_endpoint(
    task_id: str = Path(..., description="The task ID to retrieve"),
) -> TaskResponse:
    """Retrieve a specific task by its ID."""
    task = get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.post("/", response_model=TaskResponse, status_code=201, summary="Create a new task")
def create_task_endpoint(
    task_in: TaskCreate = Body(..., description="Task creation payload"),
) -> TaskResponse:
    """Create a new task associated with an optional scientific target."""
    task = create_task(task_in)
    return task


@router.put("/{task_id}", response_model=TaskResponse, summary="Update a task")
def update_task_endpoint(
    task_id: str = Path(..., description="The task ID to update"),
    task_in: TaskUpdate = Body(..., description="Task update payload"),
) -> TaskResponse:
    """Update a task's properties (title, priority, status, target, due date)."""
    task = update_task(task_id, task_in)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.delete("/{task_id}", summary="Delete a task")
def delete_task_endpoint(
    task_id: str = Path(..., description="The task ID to delete"),
) -> dict:
    """Delete a task by ID. Returns success status."""
    success = delete_task(task_id)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"detail": "Task deleted successfully"}


@router.get("/target/{target_id}", response_model=TaskResponse, summary="Get task by target ID")
def get_task_by_target_endpoint(
    target_id: str = Path(..., description="The scientific target ID"),
) -> TaskResponse:
    """Retrieve the task associated with a specific scientific target."""
    task = get_task_by_target(target_id)
    if not task:
        raise HTTPException(status_code=404, detail="No task found for this target")
    return task