from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class JournalBase(BaseModel):
    title: str = Field(max_length=255)
    description: str | None = None


class JournalCreate(JournalBase):
    owner_id: UUID


class JournalRead(JournalBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    owner_id: UUID
    created_at: datetime
    updated_at: datetime


class ArticleBase(BaseModel):
    title: str = Field(max_length=255)
    slug: str = Field(max_length=255)
    content_json: dict[str, Any]
    content_text: str = ""


class ArticleCreate(ArticleBase):
    journal_id: UUID


class ArticleRead(ArticleBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    journal_id: UUID
    created_at: datetime
    updated_at: datetime


class ArticleLinkBase(BaseModel):
    from_article_id: UUID
    to_article_id: UUID
    anchor_text: str = Field(max_length=255)


class ArticleLinkCreate(ArticleLinkBase):
    pass


class ArticleLinkRead(ArticleLinkBase):
    model_config = ConfigDict(from_attributes=True)

    created_at: datetime


class ArticleSequenceBase(BaseModel):
    journal_id: UUID
    from_article_id: UUID
    to_article_id: UUID
    order_index: int = Field(ge=0)


class ArticleSequenceCreate(ArticleSequenceBase):
    pass


class ArticleSequenceRead(ArticleSequenceBase):
    model_config = ConfigDict(from_attributes=True)
