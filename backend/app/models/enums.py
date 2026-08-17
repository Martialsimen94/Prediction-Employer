"""Domain enumerations shared by ORM models, schemas and services."""

from enum import StrEnum


class EmploymentStatus(StrEnum):
    ACTIVE = "active"
    ON_LEAVE = "on_leave"
    TERMINATED = "terminated"


class SalaryChangeReason(StrEnum):
    INITIAL = "initial"
    RAISE = "raise"
    PROMOTION = "promotion"
    ADJUSTMENT = "adjustment"
    CORRECTION = "correction"


class AbsenceType(StrEnum):
    SICK = "sick"
    VACATION = "vacation"
    UNPAID = "unpaid"
    OTHER = "other"


class TrainingStatus(StrEnum):
    ENROLLED = "enrolled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ModelStage(StrEnum):
    STAGING = "staging"
    PRODUCTION = "production"
    ARCHIVED = "archived"


class RecommendationAction(StrEnum):
    SALARY_INCREASE = "salary_increase"
    TRAINING = "training"
    PROMOTION = "promotion"
    INTERNAL_MOBILITY = "internal_mobility"
    COACHING = "coaching"
    TEAM_CHANGE = "team_change"
    WORKLOAD_REDUCTION = "workload_reduction"
    MENTORING = "mentoring"


class RecommendationPriority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RecommendationStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    DISMISSED = "dismissed"


class AuditAction(StrEnum):
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
