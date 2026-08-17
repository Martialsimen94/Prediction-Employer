"""seed default roles and permissions

Revision ID: 4a06f51a9827
Revises: 977e01171c99
Create Date: 2026-08-17 19:41:50.682990
"""

from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

revision: str = "4a06f51a9827"
down_revision: str | None = "977e01171c99"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

ROLES = ["admin", "hr", "manager", "data_scientist", "employee"]

PERMISSIONS = [
    ("employees:read", "View employee records"),
    ("employees:write", "Create/update employee records"),
    ("salaries:read", "View salary history"),
    ("salaries:write", "Record salary changes"),
    ("predictions:read", "View attrition predictions and recommendations"),
    ("predictions:write", "Trigger predictions and manage recommendations"),
    ("users:manage", "Manage user accounts and role assignments"),
    ("audit:read", "View the audit log"),
]

ROLE_PERMISSIONS = {
    "admin": [code for code, _ in PERMISSIONS],
    "hr": [
        "employees:read",
        "employees:write",
        "salaries:read",
        "salaries:write",
        "predictions:read",
        "audit:read",
    ],
    "manager": ["employees:read", "predictions:read"],
    "data_scientist": ["predictions:read", "predictions:write", "audit:read"],
    "employee": [],
}


def upgrade() -> None:
    conn = op.get_bind()

    role_ids: dict[str, int] = {}
    for name in ROLES:
        role_ids[name] = conn.execute(
            text("INSERT INTO roles (name) VALUES (:name) RETURNING id"), {"name": name}
        ).scalar_one()

    permission_ids: dict[str, int] = {}
    for code, description in PERMISSIONS:
        permission_ids[code] = conn.execute(
            text("INSERT INTO permissions (code, description) VALUES (:code, :description) RETURNING id"),
            {"code": code, "description": description},
        ).scalar_one()

    for role_name, codes in ROLE_PERMISSIONS.items():
        for code in codes:
            conn.execute(
                text(
                    "INSERT INTO role_permissions (role_id, permission_id) VALUES (:role_id, :permission_id)"
                ),
                {"role_id": role_ids[role_name], "permission_id": permission_ids[code]},
            )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(text("DELETE FROM role_permissions"))
    conn.execute(text("DELETE FROM permissions WHERE code = ANY(:codes)"), {"codes": [c for c, _ in PERMISSIONS]})
    conn.execute(text("DELETE FROM roles WHERE name = ANY(:names)"), {"names": ROLES})
