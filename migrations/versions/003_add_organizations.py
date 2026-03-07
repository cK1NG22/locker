"""Add organizations and org_members tables, add org_id to teams.

Revision ID: 003
Create Date: 2026-03-07
"""
from alembic import op
import sqlalchemy as sa

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("slug", sa.Text, nullable=False, unique=True),
        sa.Column("owner_id", sa.Text, nullable=False),
        sa.Column("skill_convention", sa.Text, nullable=False, server_default="/l"),
        sa.Column("created_at", sa.Text, nullable=False),
    )
    op.create_index("ix_organizations_slug", "organizations", ["slug"], unique=True)

    op.create_table(
        "org_members",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("org_id", sa.Text, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Text, nullable=False),
        sa.Column("role", sa.Text, nullable=False, server_default="member"),
        sa.UniqueConstraint("org_id", "user_id"),
    )
    op.create_index("ix_org_members_user_id", "org_members", ["user_id"])

    op.add_column("teams", sa.Column("org_id", sa.Text, sa.ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True))


def downgrade() -> None:
    op.drop_column("teams", "org_id")
    op.drop_table("org_members")
    op.drop_table("organizations")
