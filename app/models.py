from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.types import JSON

from .database import Base

jsonb_type = JSONB().with_variant(JSON(), "sqlite")


class Journal(Base):
    __tablename__ = "journals"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    slug = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)

    owner = relationship("User", back_populates="journals")
    articles = relationship("Article", back_populates="journal", cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    journals = relationship("Journal", back_populates="owner", cascade="all, delete-orphan")
    articles = relationship("Article", back_populates="owner", cascade="all, delete-orphan")


class Article(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    journal_id = Column(Integer, ForeignKey("journals.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    slug = Column(String(255), nullable=False, unique=True, index=True)
    content_json = Column(jsonb_type, nullable=False, default=dict)
    content_text = Column(Text, nullable=False, default="")
    is_index = Column(Boolean, nullable=False, default=False)
    index_entries = Column(jsonb_type, nullable=False, default=list)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    owner = relationship("User", back_populates="articles")
    journal = relationship("Journal", back_populates="articles")
    outgoing_links = relationship(
        "ArticleLink",
        back_populates="from_article",
        foreign_keys="ArticleLink.from_article_id",
        cascade="all, delete-orphan",
    )
    incoming_links = relationship(
        "ArticleLink",
        back_populates="to_article",
        foreign_keys="ArticleLink.to_article_id",
        cascade="all, delete-orphan",
    )
    sequence_entries = relationship("ArticleSequence", back_populates="article", cascade="all, delete-orphan")


class ArticleLink(Base):
    __tablename__ = "article_links"
    __table_args__ = (UniqueConstraint("from_article_id", "to_article_id", "anchor", name="uq_article_links_from_to_anchor"),)


    id = Column(Integer, primary_key=True, index=True)
    from_article_id = Column(Integer, ForeignKey("articles.id", ondelete="CASCADE"), nullable=False, index=True)
    to_article_id = Column(Integer, ForeignKey("articles.id", ondelete="CASCADE"), nullable=False, index=True)
    anchor = Column(String(255), nullable=False)

    from_article = relationship("Article", foreign_keys=[from_article_id], back_populates="outgoing_links")
    to_article = relationship("Article", foreign_keys=[to_article_id], back_populates="incoming_links")


class ArticleSequence(Base):
    __tablename__ = "article_sequence"
    __table_args__ = (
        UniqueConstraint("journal_id", "article_id", name="uq_article_sequence_journal_article"),
        UniqueConstraint("journal_id", "position", name="uq_article_sequence_journal_position"),
    )

    id = Column(Integer, primary_key=True, index=True)
    journal_id = Column(Integer, ForeignKey("journals.id", ondelete="CASCADE"), nullable=False, index=True)
    article_id = Column(Integer, ForeignKey("articles.id", ondelete="CASCADE"), nullable=False, index=True)
    position = Column(Integer, nullable=False)

    journal = relationship("Journal")
    article = relationship("Article", back_populates="sequence_entries")
