"""Initial schema — all 8 tables for Postgres.

Revision ID: 001
Create Date: 2026-03-05
"""
from alembic import op
import sqlalchemy as sa

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("email", sa.Text, nullable=False, unique=True),
        sa.Column("name", sa.Text),
        sa.Column("google_id", sa.Text, nullable=False, unique=True),
        sa.Column("created_at", sa.Text, nullable=False),
    )

    op.create_table(
        "skills",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("visibility", sa.Text, nullable=False, server_default="open"),
        sa.Column("scope", sa.Text, nullable=False, server_default="team"),
        sa.Column("uploaded_by", sa.Text),
        sa.Column("created_at", sa.Text, nullable=False),
        sa.Column("updated_at", sa.Text, nullable=False),
    )

    op.create_table(
        "teams",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("name", sa.Text, nullable=False, unique=True),
        sa.Column("token", sa.Text, nullable=False, unique=True),
        sa.Column("owner_id", sa.Text),
        sa.Column("created_at", sa.Text, nullable=False),
    )

    op.create_table(
        "team_members",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("team_id", sa.Text, sa.ForeignKey("teams.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Text, nullable=False),
        sa.Column("role", sa.Text, nullable=False, server_default="member"),
        sa.Column("can_share", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.Text, nullable=False),
        sa.UniqueConstraint("team_id", "user_id"),
    )

    op.create_table(
        "team_skills",
        sa.Column("team_id", sa.Text, sa.ForeignKey("teams.id", ondelete="CASCADE"), nullable=False),
        sa.Column("skill_id", sa.Text, sa.ForeignKey("skills.id", ondelete="CASCADE"), nullable=False),
        sa.PrimaryKeyConstraint("team_id", "skill_id"),
    )

    op.create_table(
        "skill_files",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("skill_id", sa.Text, sa.ForeignKey("skills.id", ondelete="CASCADE"), nullable=False),
        sa.Column("path", sa.Text, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("size_bytes", sa.Integer, nullable=False),
        sa.Column("created_at", sa.Text, nullable=False),
        sa.UniqueConstraint("skill_id", "path"),
    )

    op.create_table(
        "skill_usage",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("skill_name", sa.Text, nullable=False),
        sa.Column("team_id", sa.Text),
        sa.Column("invoked_at", sa.Text, nullable=False),
        sa.Column("source", sa.Text, nullable=False),
    )

    op.create_table(
        "skill_feedback",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("skill_id", sa.Text, sa.ForeignKey("skills.id", ondelete="CASCADE"), nullable=False),
        sa.Column("team_id", sa.Text),
        sa.Column("feedback_text", sa.Text, nullable=False),
        sa.Column("status", sa.Text, nullable=False, server_default="pending"),
        sa.Column("created_at", sa.Text, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("skill_feedback")
    op.drop_table("skill_usage")
    op.drop_table("skill_files")
    op.drop_table("team_skills")
    op.drop_table("team_members")
    op.drop_table("teams")
    op.drop_table("skills")
    op.drop_table("users")
