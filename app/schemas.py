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


class ArticleCreate(ArticleBase):
    pass


class ArticleUpdate(BaseModel):
    title: str | None = None
    slug: str | None = None
    content_json: dict[str, Any] | None = None


class ArticleOut(BaseModel):
    id: int
    journal_id: int
    title: str
    slug: str
    content_json: dict[str, Any]
    content_text: str

    class Config:
        from_attributes = True
