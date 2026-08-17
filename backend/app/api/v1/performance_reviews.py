"""Performance review endpoints, nested under an employee."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.db import get_db
from app.schemas.common import Page
from app.schemas.performance_review import (
    PerformanceReviewCreate,
    PerformanceReviewRead,
    PerformanceReviewUpdate,
)
from app.services.performance_review_service import PerformanceReviewService

router = APIRouter(
    prefix="/employees/{employee_id}/performance-reviews", tags=["performance-reviews"]
)


@router.get("", response_model=Page[PerformanceReviewRead])
def list_performance_reviews(
    employee_id: int,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _user: object = Depends(require_permission("employees:read")),
) -> Page[PerformanceReviewRead]:
    items, total = PerformanceReviewService(db).list_for_employee(
        employee_id, limit=limit, offset=offset
    )
    return Page(
        items=[PerformanceReviewRead.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=PerformanceReviewRead, status_code=status.HTTP_201_CREATED)
def create_performance_review(
    employee_id: int,
    payload: PerformanceReviewCreate,
    db: Session = Depends(get_db),
    _user: object = Depends(require_permission("employees:write")),
) -> PerformanceReviewRead:
    review = PerformanceReviewService(db).create(employee_id, **payload.model_dump())
    db.commit()
    return PerformanceReviewRead.model_validate(review)


@router.get("/{review_id}", response_model=PerformanceReviewRead)
def get_performance_review(
    employee_id: int,
    review_id: int,
    db: Session = Depends(get_db),
    _user: object = Depends(require_permission("employees:read")),
) -> PerformanceReviewRead:
    return PerformanceReviewRead.model_validate(PerformanceReviewService(db).get(review_id))


@router.patch("/{review_id}", response_model=PerformanceReviewRead)
def update_performance_review(
    employee_id: int,
    review_id: int,
    payload: PerformanceReviewUpdate,
    db: Session = Depends(get_db),
    _user: object = Depends(require_permission("employees:write")),
) -> PerformanceReviewRead:
    review = PerformanceReviewService(db).update(
        review_id, **payload.model_dump(exclude_unset=True)
    )
    db.commit()
    return PerformanceReviewRead.model_validate(review)
