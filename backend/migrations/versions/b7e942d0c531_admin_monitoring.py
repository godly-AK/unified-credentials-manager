"""Administrator role and security alert reviews.

Revision ID: b7e942d0c531
Revises: 02ab954e12a1
"""
from alembic import op
import sqlalchemy as sa


revision = "b7e942d0c531"
down_revision = "02ab954e12a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("is_admin", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.create_table(
        "security_alert_reviews",
        sa.Column("event_id", sa.Integer(), sa.ForeignKey("security_events.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("reviewed_by", sa.String(), nullable=False),
        sa.Column("note", sa.String(length=500), nullable=False),
        sa.Column("reviewed_at", sa.TIMESTAMP(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("security_alert_reviews")
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("is_admin")
