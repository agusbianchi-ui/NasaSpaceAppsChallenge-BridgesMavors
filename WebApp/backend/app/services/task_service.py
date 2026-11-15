from typing import Optional, Dict, List
from datetime import datetime

from app.schemas.task import Task, TaskCreate, TaskUpdate

# In-memory task storage (persists while the server runs)
_tasks: Dict[str, Task] = {}


def list_tasks() -> List[Task]:
    """Return all tasks, sorted by creation date (newest first)."""
    return sorted(_tasks.values(), key=lambda t: t.created_at, reverse=True)


def get_task(task_id: str) -> Optional[Task]:
    """Retrieve a task by its ID."""
    return _tasks.get(task_id)


def create_task(task_in: TaskCreate) -> Task:
    """Create a new task and store it in-memory."""
    task = Task(**task_in.model_dump(exclude_unset=True))
    _tasks[task.id] = task
    return task


def update_task(task_id: str, task_in: TaskUpdate) -> Optional[Task]:
    """Update an existing task."""
    task = _tasks.get(task_id)
    if not task:
        return None
    update_data = task_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)
    task.updated_at = datetime.utcnow().isoformat()
    return task


def delete_task(task_id: str) -> bool:
    """Delete a task by ID."""
    if task_id in _tasks:
        del _tasks[task_id]
        return True
    return False


def get_task_by_target(target_id: str) -> Optional[Task]:
    """Find a task by its associated scientific target ID."""
    for task in _tasks.values():
        if task.target_id == target_id:
            return task
    return None