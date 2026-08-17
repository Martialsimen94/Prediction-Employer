"""Salary endpoints, nested under an employee."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.db import get_db
from app.schemas.common import Page
from app.schemas.salary import SalaryCreate, SalaryRead
from app.services.salary_service import SalaryService

router = APIRouter(prefix="/employees/{employee_id}/salaries", tags=["salaries"])


@router.get("", response_model=Page[SalaryRead])
def list_salaries(
    employee_id: int,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _user: object = Depends(require_permission("salaries:read")),
) -> Page[SalaryRead]:
    items, total = SalaryService(db).list_for_employee(employee_id, limit=limit, offset=offset)
    return Page(
        items=[SalaryRead.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=SalaryRead, status_code=status.HTTP_201_CREATED)
def create_salary(
    employee_id: int,
    payload: SalaryCreate,
    db: Session = Depends(get_db),
    _user: object = Depends(require_permission("salaries:write")),
) -> SalaryRead:
    salary = SalaryService(db).create(employee_id, **payload.model_dump())
    db.commit()
    return SalaryRead.model_validate(salary)


@router.get("/{salary_id}", response_model=SalaryRead)
def get_salary(
    employee_id: int,
    salary_id: int,
    db: Session = Depends(get_db),
    _user: object = Depends(require_permission("salaries:read")),
) -> SalaryRead:
    return SalaryRead.model_validate(SalaryService(db).get(salary_id))
