"""Employee endpoints."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.db import get_db
from app.models.enums import EmploymentStatus
from app.schemas.common import Page
from app.schemas.employee import EmployeeCreate, EmployeeRead, EmployeeUpdate
from app.services.employee_service import EmployeeService

router = APIRouter(prefix="/employees", tags=["employees"])


@router.get("", response_model=Page[EmployeeRead])
def list_employees(
    search: str | None = Query(default=None),
    department_id: int | None = Query(default=None),
    employment_status: EmploymentStatus | None = Query(default=None),
    manager_id: int | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _user: object = Depends(require_permission("employees:read")),
) -> Page[EmployeeRead]:
    items, total = EmployeeService(db).list(
        query=search,
        department_id=department_id,
        employment_status=employment_status,
        manager_id=manager_id,
        limit=limit,
        offset=offset,
    )
    return Page(
        items=[EmployeeRead.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=EmployeeRead, status_code=status.HTTP_201_CREATED)
def create_employee(
    payload: EmployeeCreate,
    db: Session = Depends(get_db),
    _user: object = Depends(require_permission("employees:write")),
) -> EmployeeRead:
    employee = EmployeeService(db).create(**payload.model_dump())
    db.commit()
    return EmployeeRead.model_validate(employee)


@router.get("/{employee_id}", response_model=EmployeeRead)
def get_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    _user: object = Depends(require_permission("employees:read")),
) -> EmployeeRead:
    return EmployeeRead.model_validate(EmployeeService(db).get(employee_id))


@router.patch("/{employee_id}", response_model=EmployeeRead)
def update_employee(
    employee_id: int,
    payload: EmployeeUpdate,
    db: Session = Depends(get_db),
    _user: object = Depends(require_permission("employees:write")),
) -> EmployeeRead:
    employee = EmployeeService(db).update(employee_id, **payload.model_dump(exclude_unset=True))
    db.commit()
    return EmployeeRead.model_validate(employee)


@router.delete("/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    _user: object = Depends(require_permission("employees:write")),
) -> None:
    EmployeeService(db).delete(employee_id)
    db.commit()
