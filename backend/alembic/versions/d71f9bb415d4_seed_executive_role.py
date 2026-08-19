"""seed executive role

Revision ID: d71f9bb415d4
Revises: 49334c1a6af5
Create Date: 2026-08-19 00:51:09.655861
"""

from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

revision: str = "d71f9bb415d4"
down_revision: str | None = "49334c1a6af5"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

# The Module 3 seed (4a06f51a9827) covers admin/hr/manager/data_scientist/
# employee but never an "executive" role, even though the product
# description (README) always named one -- Module 11's Executive dashboard
# is its first actual consumer. Read-only across the board: company-wide
# visibility, no editing.
ROLE_NAME = "executive"
PERMISSION_CODES = ["employees:read", "salaries:read", "predictions:read", "audit:read"]


def upgrade() -> None:
    conn = op.get_bind()

    role_id = conn.execute(
        text("INSERT INTO roles (name) VALUES (:name) RETURNING id"), {"name": ROLE_NAME}
    ).scalar_one()

    permission_ids = (
        conn.execute(
            text("SELECT id FROM permissions WHERE code = ANY(:codes)"),
            {"codes": PERMISSION_CODES},
        )
        .scalars()
        .all()
    )

    for permission_id in permission_ids:
        conn.execute(
            text(
                "INSERT INTO role_permissions (role_id, permission_id) "
                "VALUES (:role_id, :permission_id)"
            ),
            {"role_id": role_id, "permission_id": permission_id},
        )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        text(
            "DELETE FROM role_permissions WHERE role_id = "
            "(SELECT id FROM roles WHERE name = :name)"
        ),
        {"name": ROLE_NAME},
    )
    conn.execute(text("DELETE FROM roles WHERE name = :name"), {"name": ROLE_NAME})
