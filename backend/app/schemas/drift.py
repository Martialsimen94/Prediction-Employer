"""Data drift report response schema."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class DriftReportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    feature_name: str
    reference_period_start: date
    reference_period_end: date
    current_period_start: date
    current_period_end: date
    drift_score: Decimal
    drift_detected: bool
    method: str
    generated_at: datetime
