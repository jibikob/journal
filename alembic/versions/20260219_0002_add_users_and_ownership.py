"""add users and ownership columns

Revision ID: 20260219_0002
Revises: 20260218_0001
Create Date: 2026-02-19 00:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260219_0002"
down_revision = "20260218_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.add_column("journals", sa.Column("owner_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_journals_owner_id"), "journals", ["owner_id"], unique=False)
    op.add_column("articles", sa.Column("owner_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_articles_owner_id"), "articles", ["owner_id"], unique=False)

    op.execute("INSERT INTO users (id, email) VALUES (1, 'dev+1@local')")
    op.execute("UPDATE journals SET owner_id = 1 WHERE owner_id IS NULL")
    op.execute(
        "UPDATE articles SET owner_id = 1 WHERE owner_id IS NULL"
    )

    op.alter_column("journals", "owner_id", nullable=False)
    op.alter_column("articles", "owner_id", nullable=False)
    op.create_foreign_key("fk_journals_owner_id_users", "journals", "users", ["owner_id"], ["id"], ondelete="CASCADE")
    op.create_foreign_key("fk_articles_owner_id_users", "articles", "users", ["owner_id"], ["id"], ondelete="CASCADE")


def downgrade() -> None:
    op.drop_constraint("fk_articles_owner_id_users", "articles", type_="foreignkey")
    op.drop_constraint("fk_journals_owner_id_users", "journals", type_="foreignkey")
    op.drop_index(op.f("ix_articles_owner_id"), table_name="articles")
    op.drop_column("articles", "owner_id")
    op.drop_index(op.f("ix_journals_owner_id"), table_name="journals")
    op.drop_column("journals", "owner_id")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
