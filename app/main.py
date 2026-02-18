from fastapi import Depends, FastAPI, HTTPException, Response, status
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from .models import Article, Journal
from .schemas import (
    ArticleCreate,
    ArticleOut,
    ArticleUpdate,
    JournalCreate,
    JournalOut,
    JournalUpdate,
)
from .utils import extract_editorjs_text, slugify

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Journal API")


@app.get("/api/journals", response_model=list[JournalOut])
def list_journals(db: Session = Depends(get_db)):
    return db.query(Journal).order_by(Journal.id).all()


@app.post("/api/journals", response_model=JournalOut, status_code=status.HTTP_201_CREATED)
def create_journal(payload: JournalCreate, db: Session = Depends(get_db)):
    slug = payload.slug or slugify(payload.title)
    if db.query(Journal).filter(Journal.slug == slug).first():
        raise HTTPException(status_code=400, detail="Journal slug already exists")

    journal = Journal(title=payload.title, slug=slug, description=payload.description)
    db.add(journal)
    db.commit()
    db.refresh(journal)
    return journal


@app.get("/api/journals/{journal_id}", response_model=JournalOut)
def get_journal(journal_id: int, db: Session = Depends(get_db)):
    journal = db.get(Journal, journal_id)
    if not journal:
        raise HTTPException(status_code=404, detail="Journal not found")
    return journal


@app.patch("/api/journals/{journal_id}", response_model=JournalOut)
def update_journal(journal_id: int, payload: JournalUpdate, db: Session = Depends(get_db)):
    journal = db.get(Journal, journal_id)
    if not journal:
        raise HTTPException(status_code=404, detail="Journal not found")

    if payload.title is not None:
        journal.title = payload.title

    if payload.slug is not None or (payload.slug is None and payload.title is not None):
        new_slug = payload.slug or slugify(journal.title)
        exists = db.query(Journal).filter(Journal.slug == new_slug, Journal.id != journal.id).first()
        if exists:
            raise HTTPException(status_code=400, detail="Journal slug already exists")
        journal.slug = new_slug

    if payload.description is not None:
        journal.description = payload.description

    db.commit()
    db.refresh(journal)
    return journal


@app.delete("/api/journals/{journal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_journal(journal_id: int, db: Session = Depends(get_db)):
    journal = db.get(Journal, journal_id)
    if not journal:
        raise HTTPException(status_code=404, detail="Journal not found")
    db.delete(journal)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/api/journals/{journal_id}/articles", response_model=list[ArticleOut])
def list_articles(journal_id: int, db: Session = Depends(get_db)):
    if not db.get(Journal, journal_id):
        raise HTTPException(status_code=404, detail="Journal not found")
    return db.query(Article).filter(Article.journal_id == journal_id).order_by(Article.id).all()


@app.post(
    "/api/journals/{journal_id}/articles",
    response_model=ArticleOut,
    status_code=status.HTTP_201_CREATED,
)
def create_article(journal_id: int, payload: ArticleCreate, db: Session = Depends(get_db)):
    if not db.get(Journal, journal_id):
        raise HTTPException(status_code=404, detail="Journal not found")

    slug = payload.slug or slugify(payload.title)
    if db.query(Article).filter(Article.slug == slug).first():
        raise HTTPException(status_code=400, detail="Article slug already exists")

    article = Article(
        journal_id=journal_id,
        title=payload.title,
        slug=slug,
        content_json=payload.content_json,
        content_text=extract_editorjs_text(payload.content_json),
    )
    db.add(article)
    db.commit()
    db.refresh(article)
    return article


@app.get("/api/articles/{article_id}", response_model=ArticleOut)
def get_article(article_id: int, db: Session = Depends(get_db)):
    article = db.get(Article, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return article


@app.patch("/api/articles/{article_id}", response_model=ArticleOut)
def update_article(article_id: int, payload: ArticleUpdate, db: Session = Depends(get_db)):
    article = db.get(Article, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    if payload.title is not None:
        article.title = payload.title

    if payload.slug is not None or (payload.slug is None and payload.title is not None):
        new_slug = payload.slug or slugify(article.title)
        exists = db.query(Article).filter(Article.slug == new_slug, Article.id != article.id).first()
        if exists:
            raise HTTPException(status_code=400, detail="Article slug already exists")
        article.slug = new_slug

    if payload.content_json is not None:
        article.content_json = payload.content_json
        article.content_text = extract_editorjs_text(payload.content_json)

    db.commit()
    db.refresh(article)
    return article


@app.delete("/api/articles/{article_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_article(article_id: int, db: Session = Depends(get_db)):
    article = db.get(Article, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    db.delete(article)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
