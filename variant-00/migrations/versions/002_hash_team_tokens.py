"""Hash team tokens at rest (SHA-256).

Revision ID: 002
Create Date: 2026-03-05
"""
import hashlib
from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add new columns (nullable initially)
    op.add_column("teams", sa.Column("token_hash", sa.Text(), nullable=True))
    op.add_column("teams", sa.Column("token_prefix", sa.Text(), nullable=True))

    # 2. Backfill: hash existing plaintext tokens
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, token FROM teams")).fetchall()
    for row in rows:
        token_hash = hashlib.sha256(row[1].encode()).hexdigest()
        token_prefix = row[1][:8]
        conn.execute(
            sa.text("UPDATE teams SET token_hash = :h, token_prefix = :p WHERE id = :id"),
            {"h": token_hash, "p": token_prefix, "id": row[0]},
        )

    # 3. Make columns NOT NULL
    op.alter_column("teams", "token_hash", nullable=False)
    op.alter_column("teams", "token_prefix", nullable=False)

    # 4. Drop old token column (its UNIQUE constraint goes with it)
    op.drop_column("teams", "token")

    # 5. Add unique index on token_hash
    op.create_unique_constraint("uq_teams_token_hash", "teams", ["token_hash"])


def downgrade() -> None:
    op.add_column("teams", sa.Column("token", sa.Text(), nullable=True))
    op.drop_constraint("uq_teams_token_hash", "teams", type_="unique")
    op.drop_column("teams", "token_hash")
    op.drop_column("teams", "token_prefix")
