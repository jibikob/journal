from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.types import JSON

from .database import Base

jsonb_type = JSONB().with_variant(JSON(), "sqlite")


class Journal(Base):
    __tablename__ = "journals"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    slug = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)

    articles = relationship("Article", back_populates="journal", cascade="all, delete-orphan")


class Article(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, index=True)
    journal_id = Column(Integer, ForeignKey("journals.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    slug = Column(String(255), nullable=False, unique=True, index=True)
    content_json = Column(jsonb_type, nullable=False, default=dict)
    content_text = Column(Text, nullable=False, default="")
    is_index = Column(Boolean, nullable=False, default=False)
    index_entries = Column(jsonb_type, nullable=False, default=list)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

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


class ArticleLink(Base):
    __tablename__ = "article_links"
    __table_args__ = (UniqueConstraint("from_article_id", "to_article_id", "anchor", name="uq_article_links_from_to_anchor"),)


    id = Column(Integer, primary_key=True, index=True)
    from_article_id = Column(Integer, ForeignKey("articles.id", ondelete="CASCADE"), nullable=False, index=True)
    to_article_id = Column(Integer, ForeignKey("articles.id", ondelete="CASCADE"), nullable=False, index=True)
    anchor = Column(String(255), nullable=False)

    from_article = relationship("Article", foreign_keys=[from_article_id], back_populates="outgoing_links")
    to_article = relationship("Article", foreign_keys=[to_article_id], back_populates="incoming_links")
