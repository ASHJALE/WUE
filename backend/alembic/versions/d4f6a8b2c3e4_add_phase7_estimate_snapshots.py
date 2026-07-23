"""add phase7 estimate snapshots

Revision ID: d4f6a8b2c3e4
Revises: c3e5f7a9b1d2
Create Date: 2026-07-24
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "d4f6a8b2c3e4"
down_revision: str | None = "c3e5f7a9b1d2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "phase7_estimate_snapshots",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("estimate_id", sa.BigInteger(), nullable=False),
        sa.Column("upload_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dimensions_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("recommendations_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("bom_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("quantities_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("cost_summary_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("preliminary_quotation_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["estimate_id"], ["estimates.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("estimate_id", name="uq_phase7_snapshots_estimate_id"),
        sa.UniqueConstraint("upload_id", name="uq_phase7_snapshots_upload_id"),
    )


def downgrade() -> None:
    op.drop_table("phase7_estimate_snapshots")
