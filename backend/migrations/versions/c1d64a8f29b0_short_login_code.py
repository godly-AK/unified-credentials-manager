"""Add a short, unique request code for main-phone approval.

Revision ID: c1d64a8f29b0
Revises: b7e942d0c531
"""
from alembic import op
import sqlalchemy as sa


revision = "c1d64a8f29b0"
down_revision = "b7e942d0c531"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Existing three-minute requests may remain null until they expire.
    op.add_column("login_trust_challenges", sa.Column("approval_code", sa.String(length=8), nullable=True))
    op.create_index("ix_login_trust_challenges_approval_code", "login_trust_challenges", ["approval_code"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_login_trust_challenges_approval_code", table_name="login_trust_challenges")
    with op.batch_alter_table("login_trust_challenges") as batch_op:
        batch_op.drop_column("approval_code")
