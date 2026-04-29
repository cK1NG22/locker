"""Add submitter_team_name column to skill_feedback table.

Revision ID: 005
Create Date: 2026-03-07
"""
from alembic import op
import sqlalchemy as sa

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "skill_feedback",
        sa.Column("submitter_team_name", sa.Text, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("skill_feedback", "submitter_team_name")
