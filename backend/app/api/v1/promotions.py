"""Promotion endpoints, nested under an employee."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.db import get_db
from app.schemas.common import Page
from app.schemas.promotion import PromotionCreate, PromotionRead
from app.services.promotion_service import PromotionService

router = APIRouter(prefix="/employees/{employee_id}/promotions", tags=["promotions"])


@router.get("", response_model=Page[PromotionRead])
def list_promotions(
    employee_id: int,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _user: object = Depends(require_permission("employees:read")),
) -> Page[PromotionRead]:
    items, total = PromotionService(db).list_for_employee(employee_id, limit=limit, offset=offset)
    return Page(
        items=[PromotionRead.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=PromotionRead, status_code=status.HTTP_201_CREATED)
def create_promotion(
    employee_id: int,
    payload: PromotionCreate,
    db: Session = Depends(get_db),
    _user: object = Depends(require_permission("employees:write")),
) -> PromotionRead:
    promotion = PromotionService(db).create(employee_id, **payload.model_dump())
    db.commit()
    return PromotionRead.model_validate(promotion)


@router.get("/{promotion_id}", response_model=PromotionRead)
def get_promotion(
    employee_id: int,
    promotion_id: int,
    db: Session = Depends(get_db),
    _user: object = Depends(require_permission("employees:read")),
) -> PromotionRead:
    return PromotionRead.model_validate(PromotionService(db).get(promotion_id))
