"""Track approvals by distinct node rather than fixed A/B slots.

Revision ID: d2a9e88c14f7
Revises: c1d64a8f29b0
"""
from alembic import op
import sqlalchemy as sa


revision = "d2a9e88c14f7"
down_revision = "c1d64a8f29b0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "login_node_approvals",
        sa.Column("challenge_id", sa.String(), sa.ForeignKey("login_trust_challenges.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("node_id", sa.String(), sa.ForeignKey("workplace_nodes.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("approved_at", sa.TIMESTAMP(timezone=True), nullable=False),
    )
    # Preserve approvals from requests still active when an existing lab database is migrated.
    op.execute(sa.text("""
        INSERT INTO login_node_approvals (challenge_id, node_id, approved_at)
        SELECT c.id, n.id, c.node_a_approved_at
        FROM login_trust_challenges c JOIN workplace_nodes n
          ON n.username = c.username AND n.slot = 'A' AND n.revoked_at IS NULL
        WHERE c.node_a_approved_at IS NOT NULL
    """))
    op.execute(sa.text("""
        INSERT INTO login_node_approvals (challenge_id, node_id, approved_at)
        SELECT c.id, n.id, c.node_b_approved_at
        FROM login_trust_challenges c JOIN workplace_nodes n
          ON n.username = c.username AND n.slot = 'B' AND n.revoked_at IS NULL
        WHERE c.node_b_approved_at IS NOT NULL
    """))


def downgrade() -> None:
    op.drop_table("login_node_approvals")
