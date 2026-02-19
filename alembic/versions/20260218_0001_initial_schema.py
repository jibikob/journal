"""initial schema

Revision ID: 20260218_0001
Revises:
Create Date: 2026-02-18 00:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260218_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "journals",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_journals")),
    )
    op.create_index(op.f("ix_journals_owner_id"), "journals", ["owner_id"], unique=False)

    op.create_table(
        "articles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("journal_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("content_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("content_text", sa.Text(), nullable=False),
        sa.Column("is_index", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("index_entries", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["journal_id"], ["journals.id"], name=op.f("fk_articles_journal_id_journals"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_articles")),
        sa.UniqueConstraint("journal_id", "slug", name="uq_articles_journal_slug"),
    )
    op.create_index(op.f("ix_articles_journal_id"), "articles", ["journal_id"], unique=False)

    op.create_table(
        "article_links",
        sa.Column("from_article_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("to_article_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("anchor_text", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["from_article_id"], ["articles.id"], name=op.f("fk_article_links_from_article_id_articles"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["to_article_id"], ["articles.id"], name=op.f("fk_article_links_to_article_id_articles"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("from_article_id", "to_article_id", name=op.f("pk_article_links")),
    )

    op.create_table(
        "article_sequence",
        sa.Column("journal_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("from_article_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("to_article_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["from_article_id"], ["articles.id"], name=op.f("fk_article_sequence_from_article_id_articles"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["journal_id"], ["journals.id"], name=op.f("fk_article_sequence_journal_id_journals"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["to_article_id"], ["articles.id"], name=op.f("fk_article_sequence_to_article_id_articles"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("journal_id", "order_index", name=op.f("pk_article_sequence")),
        sa.UniqueConstraint("journal_id", "from_article_id", "to_article_id", name="uq_article_sequence_journal_edge"),
    )


def downgrade() -> None:
    op.drop_table("article_sequence")
    op.drop_table("article_links")
    op.drop_index(op.f("ix_articles_journal_id"), table_name="articles")
    op.drop_table("articles")
    op.drop_index(op.f("ix_journals_owner_id"), table_name="journals")
    op.drop_table("journals")
