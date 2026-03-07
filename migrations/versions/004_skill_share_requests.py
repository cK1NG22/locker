"""Add skill_share_requests table for cross-team skill sharing.

Revision ID: 004
Create Date: 2026-03-07
"""
from alembic import op
import sqlalchemy as sa

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "skill_share_requests",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("skill_id", sa.Text, sa.ForeignKey("skills.id", ondelete="CASCADE"), nullable=False),
        sa.Column("from_team_id", sa.Text, sa.ForeignKey("teams.id", ondelete="CASCADE"), nullable=False),
        sa.Column("to_team_id", sa.Text, sa.ForeignKey("teams.id", ondelete="CASCADE"), nullable=False),
        sa.Column("requested_by", sa.Text, nullable=False),
        sa.Column("status", sa.Text, nullable=False, server_default="pending"),
        sa.Column("created_at", sa.Text, nullable=False),
        sa.Column("resolved_at", sa.Text),
        sa.Column("resolved_by", sa.Text),
    )
    op.create_index("ix_share_requests_to_team", "skill_share_requests", ["to_team_id"])
    op.create_index("ix_share_requests_status", "skill_share_requests", ["status"])


def downgrade() -> None:
    op.drop_table("skill_share_requests")
