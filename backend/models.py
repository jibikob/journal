from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db import Base


class Journal(Base):
    __tablename__ = "journals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    articles: Mapped[list[Article]] = relationship(
        "Article", back_populates="journal", cascade="all, delete-orphan"
    )
    sequence_items: Mapped[list[ArticleSequence]] = relationship(
        "ArticleSequence", back_populates="journal", cascade="all, delete-orphan"
    )


class Article(Base):
    __tablename__ = "articles"
    __table_args__ = (UniqueConstraint("journal_id", "slug", name="uq_articles_journal_slug"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    journal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("journals.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    content_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    content_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    journal: Mapped[Journal] = relationship("Journal", back_populates="articles")
    outgoing_links: Mapped[list[ArticleLink]] = relationship(
        "ArticleLink",
        back_populates="from_article",
        foreign_keys="ArticleLink.from_article_id",
        cascade="all, delete-orphan",
    )
    incoming_links: Mapped[list[ArticleLink]] = relationship(
        "ArticleLink",
        back_populates="to_article",
        foreign_keys="ArticleLink.to_article_id",
        cascade="all, delete-orphan",
    )


class ArticleLink(Base):
    __tablename__ = "article_links"

    from_article_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("articles.id", ondelete="CASCADE"),
        primary_key=True,
    )
    to_article_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("articles.id", ondelete="CASCADE"),
        primary_key=True,
    )
    anchor_text: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    from_article: Mapped[Article] = relationship(
        "Article", back_populates="outgoing_links", foreign_keys=[from_article_id]
    )
    to_article: Mapped[Article] = relationship(
        "Article", back_populates="incoming_links", foreign_keys=[to_article_id]
    )


class ArticleSequence(Base):
    __tablename__ = "article_sequence"
    __table_args__ = (
        UniqueConstraint(
            "journal_id",
            "from_article_id",
            "to_article_id",
            name="uq_article_sequence_journal_edge",
        ),
    )

    journal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("journals.id", ondelete="CASCADE"), primary_key=True
    )
    order_index: Mapped[int] = mapped_column(Integer, primary_key=True)
    from_article_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("articles.id", ondelete="CASCADE"), nullable=False
    )
    to_article_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("articles.id", ondelete="CASCADE"), nullable=False
    )

    journal: Mapped[Journal] = relationship("Journal", back_populates="sequence_items")
    from_article: Mapped[Article] = relationship("Article", foreign_keys=[from_article_id])
    to_article: Mapped[Article] = relationship("Article", foreign_keys=[to_article_id])
