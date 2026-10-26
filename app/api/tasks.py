from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import DbDep, Task, User
from app.security import UserDep

router = APIRouter(prefix="/tasks", tags=["tasks"])


class TaskIn(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    done: bool = False


class TaskOut(TaskIn):
    model_config = ConfigDict(from_attributes=True)
    id: int


def _get_owned_task(task_id: int, user: User, db: Session) -> Task:
    task = db.get(Task, task_id)
    # 404 tanto para "não existe" quanto para "não é seu": evita IDOR e enumeração de IDs
    if task is None or task.owner_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")
    return task


@router.get("", response_model=list[TaskOut])
def list_tasks(user: UserDep, db: DbDep) -> list[Task]:
    return list(db.scalars(select(Task).where(Task.owner_id == user.id)))


@router.post("", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(data: TaskIn, user: UserDep, db: DbDep) -> Task:
    task = Task(**data.model_dump(), owner_id=user.id)
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.put("/{task_id}", response_model=TaskOut)
def update_task(task_id: int, data: TaskIn, user: UserDep, db: DbDep) -> Task:
    task = _get_owned_task(task_id, user, db)
    task.title, task.done = data.title, data.done
    db.commit()
    db.refresh(task)
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, user: UserDep, db: DbDep) -> Response:
    db.delete(_get_owned_task(task_id, user, db))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
