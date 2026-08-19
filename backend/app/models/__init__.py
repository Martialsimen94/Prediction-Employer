"""ORM models package.

Every model module must be imported here so SQLAlchemy can resolve the
string-based relationship() and ForeignKey() references between them, and
so Base.metadata is complete for Alembic autogeneration.
"""

from app.models.absence import Absence
from app.models.audit import AuditLog
from app.models.auth import Permission, Role, User, role_permissions, user_roles
from app.models.base import Base
from app.models.department import Department
from app.models.employee import Employee
from app.models.ml import (
    AttritionPrediction,
    DataDriftReport,
    EmployeeFeatureSnapshot,
    MLModelRegistry,
    Recommendation,
)
from app.models.notification import Notification
from app.models.performance_review import PerformanceReview
from app.models.promotion import Promotion
from app.models.salary import Salary
from app.models.skill import EmployeeSkill, Skill
from app.models.training import EmployeeTraining, Training

__all__ = [
    "Absence",
    "AttritionPrediction",
    "AuditLog",
    "Base",
    "DataDriftReport",
    "Department",
    "Employee",
    "EmployeeFeatureSnapshot",
    "EmployeeSkill",
    "EmployeeTraining",
    "MLModelRegistry",
    "Notification",
    "Permission",
    "PerformanceReview",
    "Promotion",
    "Recommendation",
    "Role",
    "Salary",
    "Skill",
    "Training",
    "User",
    "role_permissions",
    "user_roles",
]
