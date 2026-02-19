from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class JournalBase(BaseModel):
    title: str
    slug: str | None = None
    description: str | None = None


class JournalCreate(JournalBase):
    pass


class JournalUpdate(BaseModel):
    title: str | None = None
    slug: str | None = None
    description: str | None = None


class JournalOut(BaseModel):
    id: int
    title: str
    slug: str
    description: str | None = None

    class Config:
        from_attributes = True


class ArticleBase(BaseModel):
    title: str
    slug: str | None = None
    content_json: dict[str, Any] = Field(default_factory=dict)
    is_index: bool | None = None
    index_entries: list[dict[str, Any]] | None = None


class ArticleCreate(ArticleBase):
    pass


class ArticleUpdate(BaseModel):
    title: str | None = None
    slug: str | None = None
    content_json: dict[str, Any] | None = None
    is_index: bool | None = None
    index_entries: list[dict[str, Any]] | None = None



class SequenceUpdate(BaseModel):
    article_ids: list[int] = Field(default_factory=list)


class SequenceOut(BaseModel):
    article_ids: list[int]


class ArticleNeighborsOut(BaseModel):
    prev_article_id: int | None = None
    next_article_id: int | None = None


class ArticleSearchOut(BaseModel):
    id: int
    title: str

    class Config:
        from_attributes = True


class ArticleOut(BaseModel):
    id: int
    journal_id: int
    title: str
    slug: str
    content_json: dict[str, Any]
    content_text: str
    is_index: bool
    index_entries: list[dict[str, Any]]
    updated_at: datetime

    class Config:
        from_attributes = True
