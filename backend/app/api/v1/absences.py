"""Absence endpoints, nested under an employee."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.db import get_db
from app.schemas.absence import AbsenceCreate, AbsenceRead, AbsenceUpdate
from app.schemas.common import Page
from app.services.absence_service import AbsenceService

router = APIRouter(prefix="/employees/{employee_id}/absences", tags=["absences"])


@router.get("", response_model=Page[AbsenceRead])
def list_absences(
    employee_id: int,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _user: object = Depends(require_permission("employees:read")),
) -> Page[AbsenceRead]:
    items, total = AbsenceService(db).list_for_employee(employee_id, limit=limit, offset=offset)
    return Page(
        items=[AbsenceRead.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=AbsenceRead, status_code=status.HTTP_201_CREATED)
def create_absence(
    employee_id: int,
    payload: AbsenceCreate,
    db: Session = Depends(get_db),
    _user: object = Depends(require_permission("employees:write")),
) -> AbsenceRead:
    absence = AbsenceService(db).create(employee_id, **payload.model_dump())
    db.commit()
    return AbsenceRead.model_validate(absence)


@router.get("/{absence_id}", response_model=AbsenceRead)
def get_absence(
    employee_id: int,
    absence_id: int,
    db: Session = Depends(get_db),
    _user: object = Depends(require_permission("employees:read")),
) -> AbsenceRead:
    return AbsenceRead.model_validate(AbsenceService(db).get(absence_id))


@router.patch("/{absence_id}", response_model=AbsenceRead)
def update_absence(
    employee_id: int,
    absence_id: int,
    payload: AbsenceUpdate,
    db: Session = Depends(get_db),
    _user: object = Depends(require_permission("employees:write")),
) -> AbsenceRead:
    absence = AbsenceService(db).update(absence_id, **payload.model_dump(exclude_unset=True))
    db.commit()
    return AbsenceRead.model_validate(absence)


@router.delete("/{absence_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_absence(
    employee_id: int,
    absence_id: int,
    db: Session = Depends(get_db),
    _user: object = Depends(require_permission("employees:write")),
) -> None:
    AbsenceService(db).delete(absence_id)
    db.commit()
