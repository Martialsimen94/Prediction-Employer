"""Department endpoints."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.db import get_db
from app.schemas.common import Page
from app.schemas.department import DepartmentCreate, DepartmentRead, DepartmentUpdate
from app.services.department_service import DepartmentService

router = APIRouter(prefix="/departments", tags=["departments"])


@router.get("", response_model=Page[DepartmentRead])
def list_departments(
    search: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _user: object = Depends(require_permission("employees:read")),
) -> Page[DepartmentRead]:
    items, total = DepartmentService(db).list(query=search, limit=limit, offset=offset)
    return Page(
        items=[DepartmentRead.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=DepartmentRead, status_code=status.HTTP_201_CREATED)
def create_department(
    payload: DepartmentCreate,
    db: Session = Depends(get_db),
    _user: object = Depends(require_permission("employees:write")),
) -> DepartmentRead:
    department = DepartmentService(db).create(**payload.model_dump())
    db.commit()
    return DepartmentRead.model_validate(department)


@router.get("/{department_id}", response_model=DepartmentRead)
def get_department(
    department_id: int,
    db: Session = Depends(get_db),
    _user: object = Depends(require_permission("employees:read")),
) -> DepartmentRead:
    return DepartmentRead.model_validate(DepartmentService(db).get(department_id))


@router.patch("/{department_id}", response_model=DepartmentRead)
def update_department(
    department_id: int,
    payload: DepartmentUpdate,
    db: Session = Depends(get_db),
    _user: object = Depends(require_permission("employees:write")),
) -> DepartmentRead:
    department = DepartmentService(db).update(
        department_id, **payload.model_dump(exclude_unset=True)
    )
    db.commit()
    return DepartmentRead.model_validate(department)


@router.delete("/{department_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_department(
    department_id: int,
    db: Session = Depends(get_db),
    _user: object = Depends(require_permission("employees:write")),
) -> None:
    DepartmentService(db).delete(department_id)
    db.commit()
