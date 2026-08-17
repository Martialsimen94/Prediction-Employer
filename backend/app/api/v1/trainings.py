"""Training catalog endpoints, and per-employee enrollment endpoints."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.db import get_db
from app.schemas.common import Page
from app.schemas.training import (
    EmployeeTrainingCreate,
    EmployeeTrainingRead,
    EmployeeTrainingUpdate,
    TrainingCreate,
    TrainingRead,
    TrainingUpdate,
)
from app.services.training_service import EmployeeTrainingService, TrainingService

catalog_router = APIRouter(prefix="/trainings", tags=["trainings"])
enrollment_router = APIRouter(prefix="/employees/{employee_id}/trainings", tags=["trainings"])


@catalog_router.get("", response_model=Page[TrainingRead])
def list_trainings(
    search: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _user: object = Depends(require_permission("employees:read")),
) -> Page[TrainingRead]:
    items, total = TrainingService(db).list(query=search, limit=limit, offset=offset)
    return Page(
        items=[TrainingRead.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@catalog_router.post("", response_model=TrainingRead, status_code=status.HTTP_201_CREATED)
def create_training(
    payload: TrainingCreate,
    db: Session = Depends(get_db),
    _user: object = Depends(require_permission("employees:write")),
) -> TrainingRead:
    training = TrainingService(db).create(**payload.model_dump())
    db.commit()
    return TrainingRead.model_validate(training)


@catalog_router.get("/{training_id}", response_model=TrainingRead)
def get_training(
    training_id: int,
    db: Session = Depends(get_db),
    _user: object = Depends(require_permission("employees:read")),
) -> TrainingRead:
    return TrainingRead.model_validate(TrainingService(db).get(training_id))


@catalog_router.patch("/{training_id}", response_model=TrainingRead)
def update_training(
    training_id: int,
    payload: TrainingUpdate,
    db: Session = Depends(get_db),
    _user: object = Depends(require_permission("employees:write")),
) -> TrainingRead:
    training = TrainingService(db).update(training_id, **payload.model_dump(exclude_unset=True))
    db.commit()
    return TrainingRead.model_validate(training)


@catalog_router.delete("/{training_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_training(
    training_id: int,
    db: Session = Depends(get_db),
    _user: object = Depends(require_permission("employees:write")),
) -> None:
    TrainingService(db).delete(training_id)
    db.commit()


@enrollment_router.get("", response_model=Page[EmployeeTrainingRead])
def list_enrollments(
    employee_id: int,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _user: object = Depends(require_permission("employees:read")),
) -> Page[EmployeeTrainingRead]:
    items, total = EmployeeTrainingService(db).list_for_employee(
        employee_id, limit=limit, offset=offset
    )
    return Page(
        items=[EmployeeTrainingRead.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@enrollment_router.post(
    "", response_model=EmployeeTrainingRead, status_code=status.HTTP_201_CREATED
)
def create_enrollment(
    employee_id: int,
    payload: EmployeeTrainingCreate,
    db: Session = Depends(get_db),
    _user: object = Depends(require_permission("employees:write")),
) -> EmployeeTrainingRead:
    enrollment = EmployeeTrainingService(db).enroll(employee_id, **payload.model_dump())
    db.commit()
    return EmployeeTrainingRead.model_validate(enrollment)


@enrollment_router.get("/{enrollment_id}", response_model=EmployeeTrainingRead)
def get_enrollment(
    employee_id: int,
    enrollment_id: int,
    db: Session = Depends(get_db),
    _user: object = Depends(require_permission("employees:read")),
) -> EmployeeTrainingRead:
    return EmployeeTrainingRead.model_validate(EmployeeTrainingService(db).get(enrollment_id))


@enrollment_router.patch("/{enrollment_id}", response_model=EmployeeTrainingRead)
def update_enrollment(
    employee_id: int,
    enrollment_id: int,
    payload: EmployeeTrainingUpdate,
    db: Session = Depends(get_db),
    _user: object = Depends(require_permission("employees:write")),
) -> EmployeeTrainingRead:
    enrollment = EmployeeTrainingService(db).update(
        enrollment_id, **payload.model_dump(exclude_unset=True)
    )
    db.commit()
    return EmployeeTrainingRead.model_validate(enrollment)
