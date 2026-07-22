"""Update quotation workflow statuses.

Revision ID: c3e5f7a9b1d2
Revises: b8f4d1daabca
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "c3e5f7a9b1d2"
down_revision: str | None = "b8f4d1daabca"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OLD_STATUS_CHECK = "status IN ('draft', 'issued', 'accepted', 'rejected', 'expired')"
NEW_STATUS_CHECK = "status IN ('draft', 'approved', 'rejected', 'completed')"


def upgrade() -> None:
    connection = op.get_bind()
    blocked = connection.execute(
        sa.text(
            "SELECT id, status FROM quotations "
            "WHERE status IN ('issued', 'expired') ORDER BY id"
        )
    ).all()
    if blocked:
        details = ", ".join(f"{row.id}:{row.status}" for row in blocked)
        raise RuntimeError(
            "Cannot update quotation statuses while issued or expired rows exist: "
            + details
        )

    # PostgreSQL transactional DDL keeps the constraint replacement and data
    # conversion atomic: either all three operations commit, or none do.
    op.drop_constraint("ck_quotations_status", "quotations", type_="check")
    connection.execute(
        sa.text("UPDATE quotations SET status = 'approved' WHERE status = 'accepted'")
    )
    op.create_check_constraint(
        "ck_quotations_status", "quotations", NEW_STATUS_CHECK
    )


def downgrade() -> None:
    connection = op.get_bind()
    completed_ids = connection.execute(
        sa.text("SELECT id FROM quotations WHERE status = 'completed' ORDER BY id")
    ).scalars().all()
    if completed_ids:
        raise RuntimeError(
            "Cannot downgrade while completed quotations exist; IDs: "
            + ", ".join(str(value) for value in completed_ids)
        )

    op.drop_constraint("ck_quotations_status", "quotations", type_="check")
    connection.execute(
        sa.text("UPDATE quotations SET status = 'accepted' WHERE status = 'approved'")
    )
    op.create_check_constraint(
        "ck_quotations_status", "quotations", OLD_STATUS_CHECK
    )
